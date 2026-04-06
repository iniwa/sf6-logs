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
    if matches:
        latest = matches[0]
        lp = latest.get('lp_after')
        mr = latest.get('mr_after')

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'winrate': winrate,
        'lp': lp,
        'mr': mr,
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
    if matches:
        latest = matches[0]
        lp = latest.get('lp_after')
        mr = latest.get('mr_after')

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'winrate': winrate,
        'lp': lp,
        'mr': mr,
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
