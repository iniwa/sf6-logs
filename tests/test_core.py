import sqlite3
import sys
import types

bs4_stub = types.ModuleType('bs4')
bs4_stub.BeautifulSoup = object
sys.modules.setdefault('bs4', bs4_stub)

from services import cfn_scraper, scheduler, stats, storage


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
