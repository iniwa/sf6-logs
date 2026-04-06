from datetime import datetime

import config as c
from services import storage


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
        'session_id': session['id'],
        'session_label': session.get('label'),
    }


def get_current_lp():
    matches = storage.get_matches(limit=1)
    if not matches:
        return {'lp': None, 'mr': None}
    latest = matches[0]
    return {
        'lp': latest.get('lp_after'),
        'mr': latest.get('mr_after'),
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
