"""Offline authentication recovery; no stored credentials or running app."""
from types import SimpleNamespace

import pytest
import requests

from services import cfn_auth, scheduler, storage, error_history


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    original = scheduler._status.copy()
    monkeypatch.setattr(storage, 'get_config', lambda key, default=None: {
        'mock_mode': 'false', 'poll_interval': '90',
    }.get(key, default))
    monkeypatch.setattr(storage, '_connect', lambda: pytest.fail('No database access'))
    monkeypatch.setattr(requests.sessions.Session, 'request',
                        lambda *a, **k: pytest.fail('No network access'))
    error_history.clear()
    yield
    scheduler._status.clear()
    scheduler._status.update(original)
    error_history.clear()


@pytest.mark.parametrize('url,expected', [
    ('https://www.streetfighter.com/6/buckler/ja-jp', True),
    ('https://www.streetfighter.com/6/buckler', True),
    ('https://www.streetfighter.com/6/buckler/auth/login', False),
    ('https://auth.cid.capcom.com/authorize', False),
    ('https://www.streetfighter.com.evil.test/6/buckler', False),
    ('https://www.streetfighter.com/6/buckler-other', False),
])
def test_browser_return_url(url, expected):
    assert cfn_auth._is_buckler_url(url) is expected


@pytest.mark.parametrize('domain,expected', [
    ('.streetfighter.com', True), ('www.streetfighter.com', True),
    ('notstreetfighter.com', False), ('streetfighter.com.evil.test', False),
])
def test_cookie_scope(domain, expected):
    assert cfn_auth._is_buckler_cookie(domain) is expected


def test_auth_page_403_is_safe_and_uses_browser_fallback(monkeypatch):
    response = SimpleNamespace(status_code=403, url='https://example.invalid/?state=PRIVATE')
    monkeypatch.setattr(requests.Session, 'get', lambda *a, **k: response)
    with pytest.raises(cfn_auth.LoginError) as caught:
        cfn_auth._requests_login('synthetic', 'synthetic')
    assert caught.value.status_code == 403
    assert caught.value.kind == 'auth'
    assert 'PRIVATE' not in str(caught.value)
    monkeypatch.setattr(cfn_auth, 'is_playwright_available', lambda: True)
    calls = []
    monkeypatch.setattr(cfn_auth, '_playwright_login', lambda *args: calls.append(args) or True)
    assert cfn_auth.auto_login('synthetic', 'synthetic') is True
    assert len(calls) == 1
    assert error_history.get_recent_errors()[0]['status_code'] == 403


def test_cookie_update_shortens_only_auth_backoff(monkeypatch):
    monkeypatch.setattr(scheduler.time, 'time', lambda: 1000)
    intervals = []
    monkeypatch.setattr(scheduler, '_reschedule_poll_job', lambda seconds: intervals.append(seconds) or True)
    scheduler._status.update(last_error='auth/403: synthetic', next_retry_at=2800,
                             consecutive_errors=8, is_idle_slowed=True)
    error_history.record('poll', kind='auth', status_code=403)
    assert scheduler.resume_after_cookie_update() is True
    assert scheduler._status['next_retry_at'] == 1090
    assert scheduler._status['last_error'] == 'auth/403: synthetic'
    assert scheduler._status['consecutive_errors'] == 8
    assert len(error_history.get_recent_errors()) == 1
    assert intervals == [90]
    scheduler._status.update(last_error='rate_limit/429: synthetic', next_retry_at=2800)
    assert scheduler.resume_after_cookie_update() is False
    assert scheduler._status['next_retry_at'] == 2800
    assert intervals == [90]


def test_mock_cookie_update_does_not_schedule(monkeypatch):
    monkeypatch.setattr(storage, 'get_config', lambda key, default=None: 'true')
    monkeypatch.setattr(scheduler, '_reschedule_poll_job', lambda *a: pytest.fail('mock schedule'))
    assert scheduler.resume_after_cookie_update() is False


def test_login_is_serialized_and_lock_released(monkeypatch):
    def login(*args):
        with pytest.raises(cfn_auth.LoginError, match='ログイン処理中'):
            cfn_auth.auto_login('synthetic', 'synthetic')
        return True
    monkeypatch.setattr(cfn_auth, '_requests_login', login)
    assert cfn_auth.auto_login('synthetic', 'synthetic') is True
    assert cfn_auth.auto_login('synthetic', 'synthetic') is True


def test_browser_failure_has_actionable_safe_message(monkeypatch):
    def fail(*args):
        raise RuntimeError('https://example.invalid/?state=PRIVATE')
    monkeypatch.setattr(cfn_auth, '_requests_login', fail)
    monkeypatch.setattr(cfn_auth, 'is_playwright_available', lambda: True)
    monkeypatch.setattr(cfn_auth, '_playwright_login', fail)
    with pytest.raises(cfn_auth.LoginError) as caught:
        cfn_auth.auto_login('synthetic', 'synthetic')
    assert '手動更新' in str(caught.value)
    assert 'PRIVATE' not in str(caught.value)
    assert not cfn_auth._login_lock.locked()


@pytest.mark.parametrize('action', ['cookie', 'login'])
def test_settings_resume_after_success(monkeypatch, action):
    from flask import Flask
    from routes import settings
    app = Flask(__name__)
    app.register_blueprint(settings.bp)
    events = []
    monkeypatch.setattr(cfn_auth, 'save_cookie', lambda value: events.append('saved'))
    monkeypatch.setattr(cfn_auth, 'auto_login', lambda: events.append('logged_in'))
    monkeypatch.setattr(scheduler, 'resume_after_cookie_update', lambda: events.append('resume'))
    if action == 'cookie':
        response = app.test_client().post('/settings/save_cfn', data={'cfn_cookie': 'synthetic'})
        assert events == ['saved', 'resume']
    else:
        response = app.test_client().post('/settings/test_login')
        assert events == ['logged_in', 'resume']
    assert response.status_code == 302
