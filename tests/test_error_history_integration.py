"""Offline regressions for error capture, recovery, and Dashboard output."""

import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

import config as c
from services import cfn_auth, cfn_scraper, error_history, scheduler, storage


def _raise(error):
    def fail(*args, **kwargs):
        raise error
    return fail


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    """Never read the configured DB/credentials or make an external request."""
    values = {'mock_mode': 'false', 'poll_interval': '90'}
    monkeypatch.setattr(storage, 'get_config', lambda key, default=None: values.get(key, default))
    monkeypatch.setattr(storage, '_connect', lambda: pytest.fail('database access is forbidden'))
    monkeypatch.setattr(
        requests.sessions.Session, 'request',
        lambda *args, **kwargs: pytest.fail('external network access is forbidden'),
    )
    monkeypatch.setattr(c, 'log', lambda *args, **kwargs: None)
    monkeypatch.setattr(error_history, '_errors', deque(maxlen=error_history.MAX_RECENT_ERRORS))
    monkeypatch.setattr(cfn_auth, '_build_id_cache', {'value': None})
    monkeypatch.setattr(scheduler.scheduler, 'get_job', lambda job_id: None)
    monkeypatch.setattr(scheduler, '_reschedule_poll_job', lambda seconds: True)
    with scheduler._status_lock:
        original = scheduler._status.copy()
        scheduler._status.update({
            'last_fetch': None, 'last_error': None, 'error_count': 0,
            'consecutive_errors': 0, 'next_retry_at': None, 'matches_found': 0,
            'auth_ok': None, 'auth_checked_at': None, 'auto_login_last': None,
            'normal_interval': 90, 'effective_interval': 90,
            'consecutive_empty_fetches': 0, 'is_idle_slowed': False,
        })
    yield values
    with scheduler._status_lock:
        scheduler._status.clear()
        scheduler._status.update(original)


def _prepare_poll(monkeypatch, fetch):
    monkeypatch.setattr(cfn_auth, 'get_session', lambda: object())
    monkeypatch.setattr(cfn_scraper, 'fetch_battle_log', fetch)
    monkeypatch.setattr(storage, 'match_exists', lambda replay_id: False)
    monkeypatch.setattr(storage, 'insert_match', lambda match: None)
    monkeypatch.setattr(scheduler, '_backfill_prev_after', lambda match: None)
    monkeypatch.setattr(scheduler, '_auto_session_start', lambda: None)


@pytest.mark.parametrize('failure', [
    cfn_scraper.CfnFetchError('synthetic throttling', kind='rate_limit', status_code=429),
    RuntimeError('synthetic unexpected failure'),
])
def test_successful_poll_clears_current_error_but_keeps_history(monkeypatch, failure):
    clock = {'now': 1000}
    monkeypatch.setattr(scheduler.time, 'time', lambda: clock['now'])
    _prepare_poll(monkeypatch, _raise(failure))

    scheduler._poll_job()
    history = error_history.get_recent_errors()
    assert len(history) == 1
    assert history[0]['source'] == 'poll'
    assert scheduler._status['consecutive_errors'] == 1
    assert scheduler._status['last_error']

    clock['now'] = scheduler._status['next_retry_at'] + 1
    monkeypatch.setattr(cfn_scraper, 'fetch_battle_log', lambda session: [{'replay_id': 'synthetic-match'}])
    scheduler._poll_job()
    assert scheduler._status['matches_found'] == 1
    assert scheduler._status['last_fetch']
    assert scheduler._status['last_error'] is None
    assert scheduler._status['error_count'] == 0
    assert scheduler._status['consecutive_errors'] == 0
    assert scheduler._status['next_retry_at'] is None
    assert error_history.get_recent_errors() == history

    monkeypatch.setattr(cfn_scraper, 'fetch_battle_log', lambda session: [])
    scheduler._poll_job()
    assert error_history.get_recent_errors() == history


@pytest.mark.parametrize('action', ['restore', 'interval', 'mock'])
def test_frequency_changes_do_not_erase_history(monkeypatch, isolated_state, action):
    error_history.record('poll', requests.Timeout('synthetic timeout'))
    history = error_history.get_recent_errors()
    scheduler._status.update({'is_idle_slowed': True, 'effective_interval': 300})
    if action == 'restore':
        scheduler.restore_normal_polling()
    elif action == 'interval':
        scheduler.update_poll_interval(30)
    else:
        isolated_state['mock_mode'] = 'true'
        _prepare_poll(monkeypatch, lambda session: [])
        scheduler._poll_job()
    assert error_history.get_recent_errors() == history
    assert scheduler._status['is_idle_slowed'] is False


@pytest.mark.parametrize('failure', [RuntimeError('synthetic failure'), cfn_auth.TwoFactorRequired('synthetic 2FA')])
def test_auto_login_success_keeps_previous_failure(monkeypatch, failure):
    monkeypatch.setattr(cfn_auth, 'refresh_cookie', _raise(failure))
    assert scheduler._try_auto_login() is False
    history = error_history.get_recent_errors()
    assert len(history) == 1
    assert history[0]['source'] == 'auto_login'
    expected_kind = 'two_factor' if isinstance(failure, cfn_auth.TwoFactorRequired) else 'unexpected'
    assert history[0]['kind'] == expected_kind

    monkeypatch.setattr(cfn_auth, 'refresh_cookie', lambda: True)
    assert scheduler._try_auto_login() is True
    assert scheduler._status['auth_ok'] is True
    assert error_history.get_recent_errors() == history


def test_absent_login_configuration_is_not_an_error():
    assert scheduler._try_auto_login() is False
    assert error_history.get_recent_errors() == []


def test_successful_login_fallback_keeps_requests_failure(monkeypatch):
    fallback_calls = []
    monkeypatch.setattr(cfn_auth, '_requests_login', _raise(requests.Timeout('SYNTHETIC_PRIVATE_TEXT')))
    monkeypatch.setattr(cfn_auth, 'is_playwright_available', lambda: True)
    monkeypatch.setattr(cfn_auth, '_playwright_login', lambda *args: fallback_calls.append(True) or True)
    assert cfn_auth.auto_login('sample@example.invalid', 'SYNTHETIC_PASSWORD') is True
    assert fallback_calls == [True]
    event, = error_history.get_recent_errors()
    assert event['source'] == 'auto_login_requests'
    assert event['kind'] == 'network'
    assert event['exception_type'] == 'Timeout'
    assert 'SYNTHETIC_PRIVATE_TEXT' not in json.dumps(event)


def test_two_factor_failure_is_recorded_once_without_fallback(monkeypatch, isolated_state):
    isolated_state.update({'capcom_email': 'sample@example.invalid', 'capcom_password': 'SYNTHETIC_PASSWORD'})
    monkeypatch.setattr(cfn_auth, '_requests_login', _raise(cfn_auth.TwoFactorRequired('synthetic 2FA')))
    monkeypatch.setattr(cfn_auth, 'is_playwright_available', lambda: pytest.fail('2FA must not fall back'))
    assert scheduler._try_auto_login() is False
    event, = error_history.get_recent_errors()
    assert (event['source'], event['kind']) == ('auto_login', 'two_factor')


@pytest.mark.parametrize(('status_code', 'kind'), [(401, 'auth'), (403, 'auth'), (404, 'response'), (429, 'rate_limit'), (503, 'unavailable')])
def test_build_id_http_failures_keep_status_and_category(status_code, kind):
    response = requests.Response()
    response.status_code = status_code
    response.url = 'https://example.invalid/SYNTHETIC_PRIVATE_URL'
    response._content = b'SYNTHETIC_PRIVATE_BODY'
    response.headers['Cookie'] = 'SYNTHETIC_PRIVATE_COOKIE'
    calls = []

    def get(*args, **kwargs):
        calls.append(True)
        return response

    assert cfn_auth.get_build_id(SimpleNamespace(get=get), force_refresh=True) is None
    event, = error_history.get_recent_errors()
    assert (event['source'], event['kind'], event['status_code']) == ('build_id', kind, status_code)
    assert event['exception_type'] == 'HTTPError'
    assert 'SYNTHETIC_PRIVATE' not in json.dumps(event)
    assert calls == [True]


@pytest.mark.parametrize(('script_text', 'kind'), [(None, 'response'), ('{}', 'response'), ('not JSON', 'parse'), ('[]', 'parse')])
def test_build_id_parse_failure_then_success_retains_history(monkeypatch, script_text, kind):
    node = None if script_text is None else SimpleNamespace(string=script_text)
    soup = SimpleNamespace(find=lambda *args, **kwargs: node)
    monkeypatch.setattr(cfn_auth, 'BeautifulSoup', lambda *args: soup)
    response = SimpleNamespace(status_code=200, text='synthetic HTML', raise_for_status=lambda: None)
    session = SimpleNamespace(get=lambda *args, **kwargs: response)
    assert cfn_auth.get_build_id(session, force_refresh=True) is None
    event, = error_history.get_recent_errors()
    assert (event['source'], event['kind'], event['status_code']) == ('build_id', kind, 200)

    node = SimpleNamespace(string='{"buildId":"synthetic-build"}')
    assert cfn_auth.get_build_id(session, force_refresh=True) == 'synthetic-build'
    assert error_history.get_recent_errors() == [event]


def test_build_id_network_failure_is_recorded():
    session = SimpleNamespace(get=_raise(requests.ConnectionError('SYNTHETIC_PRIVATE_URL')))
    assert cfn_auth.get_build_id(session, force_refresh=True) is None
    event, = error_history.get_recent_errors()
    assert (event['kind'], event['status_code']) == ('network', None)


@pytest.mark.parametrize('failure_site', ['config', 'session'])
def test_auth_job_records_and_reraises_uncaught_failure(monkeypatch, isolated_state, failure_site):
    failure = RuntimeError('synthetic auth-check failure')
    if failure_site == 'config':
        monkeypatch.setattr(storage, 'get_config', _raise(failure))
    else:
        isolated_state['cfn_cookie'] = 'SYNTHETIC_COOKIE'
        monkeypatch.setattr(cfn_auth, 'get_session', _raise(failure))
    with pytest.raises(RuntimeError) as caught:
        scheduler._check_auth_job()
    assert caught.value is failure
    event, = error_history.get_recent_errors()
    assert event['source'] == 'auth_check'


def test_partial_replay_parse_error_survives_successful_poll(monkeypatch):
    original_parse = cfn_scraper._parse_replay

    def parse(replay, my_id):
        if replay is None:
            return original_parse(replay, my_id)
        return {'replay_id': 'SYNTHETIC_PRIVATE_REPLAY'}

    monkeypatch.setattr(cfn_scraper, '_parse_replay', parse)
    data = {'pageProps': {'replay_list': [None, {}]}}
    _prepare_poll(monkeypatch, lambda session: cfn_scraper._parse_battle_log(data, '123'))
    scheduler._poll_job()
    assert scheduler._status['matches_found'] == 1
    assert scheduler._status['last_error'] is None
    event, = error_history.get_recent_errors()
    assert (event['source'], event['exception_type']) == ('replay_parse', 'AttributeError')
    assert 'SYNTHETIC_PRIVATE_REPLAY' not in json.dumps(event)


def test_history_order_and_snapshot_copies(monkeypatch):
    start = datetime(2026, 8, 31, 9, 31, 42, tzinfo=c.JST)
    for index in range(23):
        monkeypatch.setattr(c, 'get_now', lambda index=index: start + timedelta(seconds=index))
        returned = error_history.record('poll', RuntimeError('synthetic'), status_code=400 + index)
        returned['source'] = 'changed'
    snapshot = error_history.get_recent_errors()
    assert [event['status_code'] for event in snapshot] == list(range(422, 402, -1))
    assert [event['timestamp'] for event in snapshot] == sorted((event['timestamp'] for event in snapshot), reverse=True)
    snapshot[0]['summary'] = 'changed'
    snapshot.clear()
    assert len(error_history.get_recent_errors()) == 20
    assert error_history.get_recent_errors()[0]['source'] == 'poll'
    assert error_history.get_recent_errors()[0]['summary'] != 'changed'


@pytest.mark.parametrize('status_code', ['SYNTHETIC_PRIVATE_CODE', [], True, 999, float('inf')])
def test_invalid_diagnostic_metadata_is_not_exposed(status_code):
    event = error_history.record('SYNTHETIC_PRIVATE_SOURCE', RuntimeError('SYNTHETIC_PRIVATE_MESSAGE'), kind='SYNTHETIC_PRIVATE_KIND', status_code=status_code)
    assert event['status_code'] is None
    assert event['source'] == 'unexpected'
    assert event['kind'] == 'unexpected'
    assert 'SYNTHETIC_PRIVATE' not in json.dumps(event)


def test_cfn_fetch_category_is_preserved_over_http_inference():
    event = error_history.record('poll', cfn_scraper.CfnFetchError('synthetic', kind='response', status_code=503))
    assert (event['kind'], event['status_code']) == ('response', 503)


@pytest.mark.parametrize('attribute', ['kind', 'status_code', 'response'])
def test_unreadable_exception_metadata_does_not_interrupt_auto_login(monkeypatch, attribute):
    def broken_metadata(self):
        raise RuntimeError('synthetic metadata access failure')

    failure_type = type('MetadataError', (Exception,), {attribute: property(broken_metadata)})
    monkeypatch.setattr(cfn_auth, 'refresh_cookie', _raise(failure_type('synthetic login failure')))
    assert scheduler._try_auto_login() is False
    assert scheduler._status['auto_login_last'] == 'failed: synthetic login failure'
    event, = error_history.get_recent_errors()
    assert event['source'] == 'auto_login'
    assert event['exception_type'] == 'MetadataError'


def test_unreadable_response_status_is_ignored():
    class BrokenResponse:
        @property
        def status_code(self):
            raise RuntimeError('synthetic response access failure')

    failure = RuntimeError('synthetic failure')
    failure.response = BrokenResponse()
    event = error_history.record('build_id', failure)
    assert event['status_code'] is None
    assert event['kind'] == 'unexpected'


@pytest.fixture
def web_app(monkeypatch):
    flask = pytest.importorskip('flask')
    from routes import api, dashboard, settings
    from routes.filters import register_filters

    app = flask.Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
    app.config['TESTING'] = True
    app.register_blueprint(api.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(settings.bp)
    register_filters(app)
    today = {'wins': 0, 'losses': 0, 'total': 0, 'winrate': 0, 'is_master': False, 'lp': None, 'lp_delta': None}
    monkeypatch.setattr(dashboard.stats, 'get_today_stats', lambda *args, **kwargs: today)
    for name in ('get_character_stats', 'get_opponent_stats', 'get_lp_mr_history'):
        monkeypatch.setattr(dashboard.stats, name, lambda *args, **kwargs: [])
    monkeypatch.setattr(storage, 'get_matches', lambda *args, **kwargs: [])
    monkeypatch.setattr(storage, 'get_matches_since', lambda *args, **kwargs: [])
    monkeypatch.setattr(
        storage, 'load_all_config',
        lambda: {'mock_mode': 'false', 'poll_interval': '90'},
    )
    return app


@pytest.mark.parametrize('failure', [RuntimeError('synthetic login failure'), cfn_auth.TwoFactorRequired('synthetic 2FA')])
def test_login_test_failure_records_event_without_changing_redirect(monkeypatch, web_app, failure):
    monkeypatch.setattr(cfn_auth, 'auto_login', _raise(failure))
    response = web_app.test_client().post('/settings/test_login')
    assert response.status_code == 302
    assert '/settings?msg=login_fail' in response.headers['Location']
    event, = error_history.get_recent_errors()
    assert event['source'] == 'login_test'
    assert event['kind'] == ('two_factor' if isinstance(failure, cfn_auth.TwoFactorRequired) else 'unexpected')


def test_api_history_is_safe_additive_and_cached(monkeypatch, web_app):
    failure = requests.HTTPError('SYNTHETIC_PRIVATE_MESSAGE')
    failure.response = requests.Response()
    failure.response.status_code = 403
    failure.response.url = 'https://example.invalid/SYNTHETIC_PRIVATE_URL'
    failure.response.headers['Authorization'] = 'SYNTHETIC_PRIVATE_HEADER'
    failure.response._content = b'SYNTHETIC_PRIVATE_BODY'
    event = error_history.record('build_id', failure)
    scheduler._status['auth_ok'] = True
    monkeypatch.setattr(cfn_auth, 'get_session', lambda: pytest.fail('status must not contact CFN'))
    monkeypatch.setattr(cfn_auth, 'get_build_id', lambda *args, **kwargs: pytest.fail('status must not check auth'))
    client = web_app.test_client()
    for _ in range(2):
        response = client.get('/api/status')
        assert response.status_code == 200
        payload = response.get_json()
        assert set(payload) == {'scheduler', 'authenticated', 'mock_mode'}
        assert payload['authenticated'] is True
        assert payload['scheduler']['recent_errors'] == [event]
        assert payload['scheduler']['recent_errors_limit'] == 20
        assert 'SYNTHETIC_PRIVATE' not in json.dumps(payload['scheduler']['recent_errors'])
    assert error_history.get_recent_errors() == [event]


def test_history_moves_from_dashboard_to_settings(monkeypatch, web_app):
    client = web_app.test_client()
    dashboard = client.get('/').get_data(as_text=True)
    empty = client.get('/settings').get_data(as_text=True)
    assert '直近のエラー履歴' not in dashboard
    assert 'recent-errors-card' not in dashboard
    assert '直近のエラー履歴' in empty
    assert 'エラー履歴はありません。' in empty
    assert '直近20件' in empty
    assert 'アプリ再起動時に消去' in empty
    monkeypatch.setattr(c, 'get_now', lambda: datetime(2026, 8, 31, 9, 31, 42, tzinfo=c.JST))
    error_history.record('poll', cfn_scraper.CfnFetchError('SYNTHETIC_PRIVATE_MESSAGE', kind='rate_limit', status_code=429))
    populated = client.get('/settings').get_data(as_text=True)
    assert '2026-08-31 09:31:42 JST' in populated
    assert 'リクエスト制限 (rate_limit)' in populated
    assert '<td>429</td>' in populated
    assert 'エラー履歴はありません。' not in populated
    assert 'SYNTHETIC_PRIVATE' not in populated


def test_initial_history_html_escapes_all_event_text(monkeypatch, web_app):
    event = error_history.record('poll', RuntimeError('synthetic'))
    event.update({'source_label': '<img src=x>', 'summary': '<script>bad()</script>', 'exception_type': '<b>type</b>'})
    monkeypatch.setattr(error_history, 'get_recent_errors', lambda: [event])
    html = web_app.test_client().get('/settings').get_data(as_text=True)
    assert '&lt;img src=x&gt;' in html
    assert '&lt;script&gt;bad()&lt;/script&gt;' in html
    assert '&lt;b&gt;type&lt;/b&gt;' in html
    assert '<script>bad()</script>' not in html
