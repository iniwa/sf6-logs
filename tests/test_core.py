import sqlite3
import sys
import threading
import types
from datetime import datetime

import pytest
import requests

try:
    from flask import Flask
except ImportError:
    Flask = None

bs4_stub = types.ModuleType('bs4')
bs4_stub.BeautifulSoup = object
sys.modules.setdefault('bs4', bs4_stub)

from services import cfn_scraper, scheduler, stats, storage


class _FakeResponse:
    def __init__(self, status_code=200, data=None, headers=None, json_error=None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}
        self._json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}')

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._data


class _FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def get(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.response


def _fetch_real(monkeypatch, response=None, error=None):
    monkeypatch.setattr(
        cfn_scraper.storage,
        'get_config',
        lambda key, default=None: '12345' if key == 'cfn_user_id' else default,
    )
    monkeypatch.setattr(cfn_scraper, 'get_build_id', lambda session: 'build-id')
    monkeypatch.setattr(
        cfn_scraper,
        'build_api_url',
        lambda path, build_id=None: 'https://example.invalid/battlelog.json',
    )
    return cfn_scraper._fetch_real_battle_log(
        _FakeSession(response=response, error=error)
    )


def test_fetch_real_battle_log_returns_empty_list_for_valid_empty_response(monkeypatch):
    response = _FakeResponse(data={'pageProps': {'replay_list': []}})

    assert _fetch_real(monkeypatch, response=response) == []


def test_fetch_real_battle_log_classifies_network_failure(monkeypatch):
    with pytest.raises(cfn_scraper.CfnFetchError) as exc_info:
        _fetch_real(monkeypatch, error=requests.ConnectionError('offline'))

    assert exc_info.value.kind == 'network'
    assert exc_info.value.status_code is None


@pytest.mark.parametrize(
    ('status_code', 'headers', 'kind', 'retry_after'),
    [
        (403, {}, 'auth', None),
        (
            405,
            {'x-amzn-waf-action': 'challenge', 'Retry-After': '120'},
            'rate_limit',
            120,
        ),
        (429, {'Retry-After': 'invalid'}, 'rate_limit', None),
        (503, {}, 'unavailable', None),
    ],
)
def test_fetch_real_battle_log_classifies_http_failures(
        monkeypatch, status_code, headers, kind, retry_after):
    response = _FakeResponse(status_code=status_code, headers=headers)

    with pytest.raises(cfn_scraper.CfnFetchError) as exc_info:
        _fetch_real(monkeypatch, response=response)

    assert exc_info.value.kind == kind
    assert exc_info.value.status_code == status_code
    assert exc_info.value.retry_after == retry_after


def test_fetch_real_battle_log_classifies_json_failure(monkeypatch):
    response = _FakeResponse(json_error=ValueError('invalid json'))

    with pytest.raises(cfn_scraper.CfnFetchError) as exc_info:
        _fetch_real(monkeypatch, response=response)

    assert exc_info.value.kind == 'response'


@pytest.mark.parametrize(
    'data',
    [
        {},
        {'pageProps': {}},
        {'pageProps': {'replay_list': None}},
        {'pageProps': {'replay_list': {}}},
    ],
)
def test_fetch_real_battle_log_rejects_malformed_payload(monkeypatch, data):
    response = _FakeResponse(data=data)

    with pytest.raises(cfn_scraper.CfnFetchError) as exc_info:
        _fetch_real(monkeypatch, response=response)

    assert exc_info.value.kind == 'response'


@pytest.fixture
def polling_state():
    with scheduler._status_lock:
        original = scheduler._status.copy()
        scheduler._status.update({
            'last_fetch': None,
            'last_error': None,
            'error_count': 0,
            'matches_found': 0,
            'auth_ok': None,
            'auth_checked_at': None,
            'consecutive_errors': 0,
            'next_retry_at': None,
            'normal_interval': 90,
            'effective_interval': 90,
            'consecutive_empty_fetches': 0,
            'is_idle_slowed': False,
        })
    yield
    with scheduler._status_lock:
        scheduler._status.clear()
        scheduler._status.update(original)


def _prepare_poll_job(monkeypatch, *, matches=None, error=None, mock_mode=False):
    values = {
        'mock_mode': 'true' if mock_mode else 'false',
        'poll_interval': '90',
    }
    monkeypatch.setattr(
        scheduler.storage,
        'get_config',
        lambda key, default=None: values.get(key, default),
    )
    monkeypatch.setattr(scheduler.cfn_auth, 'get_session', lambda: object())
    if error is not None:
        def fetch(_session):
            raise error
        monkeypatch.setattr(scheduler.cfn_scraper, 'fetch_battle_log', fetch)
    else:
        monkeypatch.setattr(
            scheduler.cfn_scraper,
            'fetch_battle_log',
            lambda _session: list(matches or []),
        )
    monkeypatch.setattr(scheduler.storage, 'match_exists', lambda _replay_id: False)
    monkeypatch.setattr(scheduler.storage, 'insert_match', lambda _match: None)
    monkeypatch.setattr(scheduler, '_backfill_prev_after', lambda _match: None)
    monkeypatch.setattr(scheduler, '_auto_session_start', lambda: None)
    monkeypatch.setattr(scheduler.c, 'log', lambda *args, **kwargs: None)


def test_poll_job_slows_after_five_valid_empty_fetches(
        monkeypatch, polling_state):
    _prepare_poll_job(monkeypatch, matches=[])
    rescheduled = []
    monkeypatch.setattr(
        scheduler,
        '_reschedule_poll_job',
        lambda seconds: rescheduled.append(seconds) or True,
    )

    for _ in range(4):
        scheduler._poll_job()
    assert rescheduled == []

    scheduler._poll_job()

    assert rescheduled == [300]
    with scheduler._status_lock:
        assert scheduler._status['consecutive_empty_fetches'] == 5
        assert scheduler._status['effective_interval'] == 300
        assert scheduler._status['is_idle_slowed'] is True


def test_poll_job_new_match_restores_normal_interval(
        monkeypatch, polling_state):
    _prepare_poll_job(monkeypatch, matches=[{'replay_id': 'new-replay'}])
    rescheduled = []
    monkeypatch.setattr(
        scheduler,
        '_reschedule_poll_job',
        lambda seconds: rescheduled.append(seconds) or True,
    )
    with scheduler._status_lock:
        scheduler._status['effective_interval'] = 300
        scheduler._status['consecutive_empty_fetches'] = 5
        scheduler._status['is_idle_slowed'] = True

    scheduler._poll_job()

    assert rescheduled == [90]
    with scheduler._status_lock:
        assert scheduler._status['consecutive_empty_fetches'] == 0
        assert scheduler._status['effective_interval'] == 90
        assert scheduler._status['is_idle_slowed'] is False
        assert scheduler._status['matches_found'] == 1


def test_poll_job_mock_empty_fetches_do_not_enter_idle(
        monkeypatch, polling_state):
    _prepare_poll_job(monkeypatch, matches=[], mock_mode=True)
    rescheduled = []
    monkeypatch.setattr(
        scheduler,
        '_reschedule_poll_job',
        lambda seconds: rescheduled.append(seconds) or True,
    )

    for _ in range(6):
        scheduler._poll_job()

    assert rescheduled == []
    with scheduler._status_lock:
        assert scheduler._status['consecutive_empty_fetches'] == 0
        assert scheduler._status['effective_interval'] == 90
        assert scheduler._status['is_idle_slowed'] is False


def test_poll_error_backoff_preserves_idle_state(
        monkeypatch, polling_state):
    error = cfn_scraper.CfnFetchError(
        'limited',
        kind='rate_limit',
        status_code=429,
        retry_after=600,
    )
    _prepare_poll_job(monkeypatch, error=error)
    monkeypatch.setattr(scheduler.time, 'time', lambda: 1000)
    with scheduler._status_lock:
        scheduler._status['normal_interval'] = 5
        scheduler._status['effective_interval'] = 300
        scheduler._status['consecutive_empty_fetches'] = 3
        scheduler._status['is_idle_slowed'] = True

    scheduler._poll_job()

    with scheduler._status_lock:
        assert scheduler._status['next_retry_at'] == 1600
        assert scheduler._status['consecutive_errors'] == 1
        assert scheduler._status['consecutive_empty_fetches'] == 3
        assert scheduler._status['effective_interval'] == 300
        assert scheduler._status['is_idle_slowed'] is True


def test_restore_normal_polling_preserves_error_backoff(
        monkeypatch, polling_state):
    monkeypatch.setattr(
        scheduler.storage,
        'get_config',
        lambda key, default=None: '90' if key == 'poll_interval' else default,
    )
    rescheduled = []
    monkeypatch.setattr(
        scheduler,
        '_reschedule_poll_job',
        lambda seconds: rescheduled.append(seconds) or True,
    )
    with scheduler._status_lock:
        scheduler._status.update({
            'last_error': 'rate_limit/429: limited',
            'error_count': 2,
            'consecutive_errors': 2,
            'next_retry_at': 2000,
            'effective_interval': 300,
            'consecutive_empty_fetches': 5,
            'is_idle_slowed': True,
        })

    scheduler.restore_normal_polling()

    assert rescheduled == [90]
    with scheduler._status_lock:
        assert scheduler._status['effective_interval'] == 90
        assert scheduler._status['consecutive_empty_fetches'] == 0
        assert scheduler._status['is_idle_slowed'] is False
        assert scheduler._status['last_error'] == 'rate_limit/429: limited'
        assert scheduler._status['error_count'] == 2
        assert scheduler._status['consecutive_errors'] == 2
        assert scheduler._status['next_retry_at'] == 2000


def test_manual_restore_serializes_with_idle_transition(
        monkeypatch, polling_state):
    _prepare_poll_job(monkeypatch, matches=[])
    with scheduler._status_lock:
        scheduler._status['consecutive_empty_fetches'] = 4

    idle_reschedule_started = threading.Event()
    allow_idle_reschedule = threading.Event()
    restore_finished = threading.Event()
    rescheduled = []

    def reschedule(seconds):
        rescheduled.append(seconds)
        if seconds == 300:
            idle_reschedule_started.set()
            allow_idle_reschedule.wait(timeout=2)
        return True

    monkeypatch.setattr(scheduler, '_reschedule_poll_job', reschedule)

    poll_thread = threading.Thread(target=scheduler._poll_job)
    poll_thread.start()
    assert idle_reschedule_started.wait(timeout=2)

    def restore():
        scheduler.restore_normal_polling()
        restore_finished.set()

    restore_thread = threading.Thread(target=restore)
    restore_thread.start()
    assert not restore_finished.wait(timeout=0.05)

    allow_idle_reschedule.set()
    poll_thread.join(timeout=2)
    restore_thread.join(timeout=2)

    assert not poll_thread.is_alive()
    assert not restore_thread.is_alive()
    assert rescheduled == [300, 90]
    with scheduler._status_lock:
        assert scheduler._status['effective_interval'] == 90
        assert scheduler._status['consecutive_empty_fetches'] == 0
        assert scheduler._status['is_idle_slowed'] is False


def test_restore_does_not_commit_state_when_job_cannot_be_rescheduled(
        monkeypatch, polling_state):
    monkeypatch.setattr(
        scheduler.storage,
        'get_config',
        lambda key, default=None: '90' if key == 'poll_interval' else default,
    )
    monkeypatch.setattr(scheduler, '_reschedule_poll_job', lambda _seconds: False)
    monkeypatch.setattr(scheduler.c, 'log', lambda *args, **kwargs: None)
    with scheduler._status_lock:
        scheduler._status.update({
            'effective_interval': 300,
            'consecutive_empty_fetches': 5,
            'is_idle_slowed': True,
        })

    assert scheduler.restore_normal_polling() is False

    with scheduler._status_lock:
        assert scheduler._status['effective_interval'] == 300
        assert scheduler._status['consecutive_empty_fetches'] == 5
        assert scheduler._status['is_idle_slowed'] is True


def test_scheduler_status_projects_retry_to_next_interval_slot(
        monkeypatch, polling_state):
    class FakeJob:
        next_run_time = datetime.fromtimestamp(1090, tz=scheduler.c.JST)

    monkeypatch.setattr(
        scheduler.scheduler,
        'get_job',
        lambda _job_id: FakeJob(),
    )
    monkeypatch.setattr(scheduler.time, 'time', lambda: 1000)
    monkeypatch.setattr(
        scheduler.storage,
        'get_config',
        lambda key, default=None: default,
    )
    with scheduler._status_lock:
        scheduler._status.update({
            'consecutive_errors': 1,
            'next_retry_at': 1180.1,
            'effective_interval': 90,
        })

    status = scheduler.get_scheduler_status()

    assert status['poll_mode'] == 'error'
    assert status['next_attempt'] == datetime.fromtimestamp(
        1270, tz=scheduler.c.JST
    ).isoformat()


@pytest.mark.skipif(Flask is None, reason='Flask is not installed')
def test_polling_normal_route_restores_scheduler_and_redirects(monkeypatch):
    from routes import dashboard as dashboard_routes
    from routes import settings as settings_routes

    calls = []
    monkeypatch.setattr(
        settings_routes.scheduler,
        'restore_normal_polling',
        lambda: calls.append(True),
    )
    app = Flask(__name__)
    app.register_blueprint(dashboard_routes.bp)
    app.register_blueprint(settings_routes.bp)

    response = app.test_client().post('/settings/polling/normal')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')
    assert calls == [True]


@pytest.mark.skipif(Flask is None, reason='Flask is not installed')
def test_enabling_mock_mode_restores_normal_polling(monkeypatch):
    from routes import settings as settings_routes

    saved = []
    restored = []
    monkeypatch.setattr(
        settings_routes.storage,
        'get_config',
        lambda key, default=None: 'false' if key == 'mock_mode' else default,
    )
    monkeypatch.setattr(
        settings_routes.storage,
        'set_config',
        lambda key, value: saved.append((key, value)),
    )
    monkeypatch.setattr(
        settings_routes.storage,
        'delete_mock_matches',
        lambda: pytest.fail('real matches must not be deleted when enabling mock'),
    )
    monkeypatch.setattr(
        settings_routes.scheduler,
        'restore_normal_polling',
        lambda: restored.append(True),
    )
    app = Flask(__name__)
    app.register_blueprint(settings_routes.bp)

    response = app.test_client().post('/settings/toggle_mock')

    assert response.status_code == 302
    assert saved == [('mock_mode', 'true')]
    assert restored == [True]


@pytest.mark.parametrize(
    ('mock_mode', 'auth_ok', 'expected'),
    [
        ('true', False, True),
        ('false', True, True),
        ('false', None, False),
    ],
)
@pytest.mark.skipif(Flask is None, reason='Flask is not installed')
def test_api_status_uses_cached_authentication(
        monkeypatch, mock_mode, auth_ok, expected):
    from routes import api as api_routes

    monkeypatch.setattr(
        api_routes.sched,
        'get_scheduler_status',
        lambda: {'auth_ok': auth_ok},
    )
    monkeypatch.setattr(
        api_routes.storage,
        'get_config',
        lambda key, default=None: mock_mode if key == 'mock_mode' else default,
    )
    app = Flask(__name__)
    app.register_blueprint(api_routes.bp)

    response = app.test_client().get('/api/status')

    assert response.status_code == 200
    assert response.get_json() == {
        'authenticated': expected,
        'mock_mode': mock_mode == 'true',
        'scheduler': {'auth_ok': auth_ok},
    }


@pytest.mark.skipif(Flask is None, reason='Flask is not installed')
def test_dashboard_template_compiles():
    from routes.filters import register_filters

    app = Flask(__name__, template_folder='../templates')
    register_filters(app)

    assert app.jinja_env.get_template('dashboard.html') is not None


def _player(short_id, character, fighter_id, result_rounds, lp=None, mr=None):
    return {
        'player': {'short_id': short_id, 'fighter_id': fighter_id},
        'playing_character_name': character,
        'round_results': result_rounds,
        'league_point': lp,
        'master_rating': mr,
    }


def _replay(replay_id, uploaded_at, battle_type, p1, p2):
    return {
        'replay_id': replay_id,
        'uploaded_at': uploaded_at,
        'replay_battle_type': battle_type,
        'player1_info': p1,
        'player2_info': p2,
    }


def test_parse_battle_log_links_lp_mr_from_newer_match_before_values():
    data = {
        'pageProps': {
            'replay_list': [
                _replay(
                    'newer',
                    1_700_000_060,
                    1,
                    _player(123, 'Ryu', 'me', [1, 1], lp=1100, mr=1510),
                    _player(999, 'Ken', 'opp1', [0, 0], lp=900, mr=1400),
                ),
                _replay(
                    'older',
                    1_700_000_000,
                    2,
                    _player(456, 'Luke', 'opp2', [1, 1], lp=800, mr=1300),
                    _player(123, 'Ryu', 'me', [0, 0], lp=1000, mr=1500),
                ),
            ]
        }
    }

    matches = cfn_scraper._parse_battle_log(data, '123')

    assert [m['replay_id'] for m in matches] == ['newer', 'older']
    assert matches[0]['result'] == 'win'
    assert matches[0]['battle_type'] == 'ranked'
    assert matches[1]['result'] == 'lose'
    assert matches[1]['battle_type'] == 'casual'
    assert matches[1]['lp_after'] == 1100
    assert matches[1]['mr_after'] == 1510


def test_parse_replay_returns_none_for_other_players():
    replay = _replay(
        'other',
        1_700_000_000,
        1,
        _player(111, 'Ryu', 'p1', [1, 1], lp=1000),
        _player(222, 'Ken', 'p2', [0, 0], lp=900),
    )

    assert cfn_scraper._parse_replay(replay, 123) is None


def test_calc_streak_counts_latest_contiguous_result():
    assert stats._calc_streak([]) == 0
    assert stats._calc_streak([
        {'result': 'win'},
        {'result': 'win'},
        {'result': 'lose'},
    ]) == 2
    assert stats._calc_streak([
        {'result': 'lose'},
        {'result': 'lose'},
        {'result': 'win'},
    ]) == -2


def test_migrate_lp_mr_fields_moves_old_after_to_before_and_chains_after():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    conn.execute(
        '''CREATE TABLE matches (
               id INTEGER PRIMARY KEY,
               played_at TEXT,
               lp_before INTEGER,
               lp_after INTEGER,
               mr_before INTEGER,
               mr_after INTEGER
           )'''
    )
    conn.executemany(
        'INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?)',
        [
            (1, '2026-01-01T10:00:00+09:00', None, 1000, None, 1500),
            (2, '2026-01-01T10:05:00+09:00', 1000, 1100, 1500, 1510),
        ],
    )

    storage._migrate_lp_mr_fields(conn)

    rows = conn.execute(
        'SELECT id, lp_before, lp_after, mr_before, mr_after FROM matches ORDER BY id'
    ).fetchall()
    assert rows == [
        (1, 1000, 1100, 1500, 1510),
        (2, 1100, None, 1510, None),
    ]
    assert conn.execute(
        "SELECT value FROM config WHERE key = 'lp_mr_migrated'"
    ).fetchone()[0] == '1'


def test_backfill_prev_after_updates_missing_values(monkeypatch):
    previous = {'id': 10, 'lp_after': None, 'mr_after': None}
    calls = []

    monkeypatch.setattr(scheduler.storage, 'get_matches', lambda limit=1: [previous])
    monkeypatch.setattr(
        scheduler.storage,
        'update_match_lp_mr',
        lambda match_id, lp_after, mr_after: calls.append((match_id, lp_after, mr_after)),
    )

    scheduler._backfill_prev_after({'lp_before': 1200, 'mr_before': 1550})

    assert calls == [(10, 1200, 1550)]
