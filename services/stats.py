from datetime import datetime

import config as c
from services import storage


def is_master():
    """最新マッチに mr_after があれば MASTER ランク到達と判定"""
    matches = storage.get_matches(limit=1)
    if matches and matches[0].get('mr_after') is not None:
        return True
    return False


def get_today_stats():
    today_start = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
    matches = storage.get_matches_since(today_start)

    wins = sum(1 for m in matches if m['result'] == 'win')
    losses = sum(1 for m in matches if m['result'] == 'lose')
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total > 0 else 0.0

    lp = None
    mr = None
    lp_delta = None
    mr_delta = None
    master = is_master()
    if matches:
        latest = matches[0]
        lp = latest.get('lp_after')
        mr = latest.get('mr_after')
        # 本日最初のマッチの before と最新の after で差分計算
        oldest = matches[-1]
        lp_start = oldest.get('lp_before')
        mr_start = oldest.get('mr_before')
        if lp is not None and lp_start is not None:
            lp_delta = lp - lp_start
        if mr is not None and mr_start is not None:
            mr_delta = mr - mr_start

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'winrate': winrate,
        'lp': lp,
        'mr': mr,
        'lp_delta': lp_delta,
        'mr_delta': mr_delta,
        'is_master': master,
    }


def get_session_stats():
    session = storage.get_current_session()
    if not session:
        return get_today_stats()

    since = datetime.fromisoformat(session['started_at'])
    matches = storage.get_matches_since(since)

    wins = sum(1 for m in matches if m['result'] == 'win')
    losses = sum(1 for m in matches if m['result'] == 'lose')
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total > 0 else 0.0

    lp = None
    mr = None
    lp_delta = None
    mr_delta = None
    if matches:
        latest = matches[0]
        lp = latest.get('lp_after')
        mr = latest.get('mr_after')
        oldest = matches[-1]
        lp_start = oldest.get('lp_before')
        mr_start = oldest.get('mr_before')
        if lp is not None and lp_start is not None:
            lp_delta = lp - lp_start
        if mr is not None and mr_start is not None:
            mr_delta = mr - mr_start

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'winrate': winrate,
        'lp': lp,
        'mr': mr,
        'lp_delta': lp_delta,
        'mr_delta': mr_delta,
        'is_master': is_master(),
        'session_id': session['id'],
        'session_label': session.get('label'),
    }


def get_current_lp():
    matches = storage.get_matches(limit=1)
    if not matches:
        return {'lp': None, 'mr': None, 'is_master': False}
    latest = matches[0]
    return {
        'lp': latest.get('lp_after'),
        'mr': latest.get('mr_after'),
        'is_master': latest.get('mr_after') is not None,
    }


def get_recent_results(count=10):
    matches = storage.get_matches(limit=count)
    return [
        {
            'result': m['result'],
            'my_character': m['my_character'],
            'opp_character': m['opp_character'],
            'opp_name': m['opp_name'],
        }
        for m in matches
    ]


def _aggregate_by(matches, key):
    """key でグループ化して W/L/勝率を集計"""
    buckets = {}
    for m in matches:
        name = m[key]
        if name not in buckets:
            buckets[name] = {'wins': 0, 'losses': 0}
        if m['result'] == 'win':
            buckets[name]['wins'] += 1
        else:
            buckets[name]['losses'] += 1

    results = []
    for name, b in buckets.items():
        total = b['wins'] + b['losses']
        results.append({
            'name': name,
            'wins': b['wins'],
            'losses': b['losses'],
            'total': total,
            'winrate': round(b['wins'] / total * 100, 1) if total > 0 else 0.0,
        })
    results.sort(key=lambda x: x['total'], reverse=True)
    return results


def get_character_stats(since_dt=None):
    if since_dt is None:
        since_dt = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
    matches = storage.get_matches_since(since_dt)
    return _aggregate_by(matches, 'my_character')


def get_matchup_stats(since_dt=None):
    if since_dt is None:
        since_dt = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
    matches = storage.get_matches_since(since_dt)
    return _aggregate_by(matches, 'opp_character')


def get_opponent_stats(since_dt=None):
    if since_dt is None:
        since_dt = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
    matches = storage.get_matches_since(since_dt)
    return _aggregate_by(matches, 'opp_name')


def get_lp_mr_history(limit=50):
    matches = storage.get_matches(limit=limit)
    matches.reverse()  # 時系列昇順
    return [
        {
            'played_at': m['played_at'],
            'lp_after': m.get('lp_after'),
            'mr_after': m.get('mr_after'),
            'result': m['result'],
        }
        for m in matches
        if m.get('lp_after') is not None or m.get('mr_after') is not None
    ]
