"""Offline checks for transient probes and consecutive failure output."""
from types import SimpleNamespace

import pytest
import requests

import config as c
from services import cfn_auth, cfn_scraper, error_history, failure_log, scheduler, storage


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(failure_log, '_counts', {})
    monkeypatch.setattr(cfn_auth, '_build_id_cache', {'value': None})
    monkeypatch.setattr(storage, 'get_config', lambda key, default=None: {
        'mock_mode': 'false', 'poll_interval': '90', 'cfn_cookie': 'synthetic',
    }.get(key, default))
    monkeypatch.setattr(storage, '_connect', lambda: pytest.fail('database access'))
    monkeypatch.setattr(requests.sessions.Session, 'request',
                        lambda *a, **k: pytest.fail('network access'))
    monkeypatch.setattr(scheduler, '_status', scheduler._status.copy())
    error_history.clear()
    yield
    error_history.clear()


def fail(error):
    def call(*args, **kwargs):
        raise error
    return call


@pytest.mark.parametrize('status', [502, 503, 429, None])
def test_transient_probe_preserves_auth_without_login(monkeypatch, status):
    response = requests.Response()
    response.status_code = status or 200
    error = requests.HTTPError(response=response) if status else requests.Timeout()
    session = SimpleNamespace(get=fail(error))
    monkeypatch.setattr(cfn_auth, 'get_session', lambda: session)
    monkeypatch.setattr(scheduler, '_try_auto_login', lambda: pytest.fail('unnecessary login'))
    scheduler._status.update(auth_ok=True, auth_checked_at='previous')
    scheduler._check_auth_job()
    assert scheduler._status['auth_ok'] is True
    assert scheduler._status['auth_checked_at'] == 'previous'
    assert len(error_history.get_recent_errors()) == 1
    # Existing callers still receive None instead of a new exception.
    assert cfn_auth.get_build_id(session) is None


@pytest.mark.parametrize('status', [401, 403])
def test_auth_rejection_still_attempts_login(monkeypatch, status):
    response = requests.Response()
    response.status_code = status
    session = SimpleNamespace(get=fail(requests.HTTPError(response=response)))
    monkeypatch.setattr(cfn_auth, 'get_session', lambda: session)
    calls = []
    monkeypatch.setattr(scheduler, '_try_auto_login', lambda: calls.append(True) or False)
    scheduler._check_auth_job()
    assert calls == [True]
    assert scheduler._status['auth_ok'] is False


def test_login_traceback_threshold_and_success_reset(monkeypatch):
    logs = []
    monkeypatch.setattr(c, 'log', lambda message, exc_info=False: logs.append((message, exc_info)))
    monkeypatch.setattr(cfn_auth, 'refresh_cookie', fail(RuntimeError('synthetic')))
    for _ in range(3):
        assert scheduler._try_auto_login() is False
    assert [trace for _, trace in logs] == [False, False, True]
    assert len(error_history.get_recent_errors()) == 3
    monkeypatch.setattr(cfn_auth, 'refresh_cookie', lambda: True)
    monkeypatch.setattr(scheduler, 'resume_after_cookie_update', lambda: False)
    assert scheduler._try_auto_login() is True
    monkeypatch.setattr(cfn_auth, 'refresh_cookie', fail(RuntimeError('synthetic')))
    scheduler._try_auto_login()
    assert logs[-1][1] is False


def test_poll_threshold_backoff_and_reset(monkeypatch):
    logs = []
    monkeypatch.setattr(c, 'log', lambda message, exc_info=False: logs.append((message, exc_info)))
    monkeypatch.setattr(cfn_auth, 'get_session', lambda: object())
    monkeypatch.setattr(cfn_scraper, 'fetch_battle_log', fail(RuntimeError('synthetic')))
    scheduler._status.update(consecutive_errors=0, next_retry_at=None, normal_interval=90)
    now = 1000
    for expected_delay in (180, 360, 720):
        monkeypatch.setattr(scheduler.time, 'time', lambda: now)
        scheduler._poll_job()
        assert scheduler._status['next_retry_at'] == now + expected_delay
        now += expected_delay
    assert sum(trace for _, trace in logs) == 1
    monkeypatch.setattr(cfn_scraper, 'fetch_battle_log', lambda session: [])
    scheduler._poll_job()
    assert scheduler._status['consecutive_errors'] == 0
    assert len(error_history.get_recent_errors()) == 3
    monkeypatch.setattr(cfn_scraper, 'fetch_battle_log', fail(RuntimeError('synthetic')))
    scheduler._poll_job()
    assert sum(trace for _, trace in logs) == 1


def test_successful_fallback_does_not_print_traceback(monkeypatch):
    logs = []
    monkeypatch.setattr(c, 'log', lambda message, exc_info=False: logs.append(exc_info))
    monkeypatch.setattr(cfn_auth, '_requests_login', fail(requests.Timeout()))
    monkeypatch.setattr(cfn_auth, 'is_playwright_available', lambda: True)
    monkeypatch.setattr(cfn_auth, '_playwright_login', lambda *a: True)
    assert cfn_auth.auto_login('synthetic', 'synthetic') is True
    assert not any(logs)
    assert len(error_history.get_recent_errors()) == 1
