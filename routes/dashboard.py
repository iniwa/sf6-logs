import re
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

import config as c
from services import storage, stats
from services import scheduler as sched
from services import cfn_auth

bp = Blueprint('dashboard', __name__)

BATTLE_MODES = [
    ('all', 'All'),
    ('ranked', 'Ranked'),
    ('casual', 'Casual'),
    ('battle_hub', 'Battle Hub'),
    ('custom', 'Custom'),
]

PERIOD_CHOICES = [
    ('last20', '直近20戦'),
    ('last100', '直近100戦'),
    ('last200', '直近200戦'),
    ('all', 'All'),
]

_PRESET_PERIODS = {v for v, _ in PERIOD_CHOICES}


def _parse_period():
    """期間パラメータを解析。(period, since_dt, selected_date, last_n) を返す。"""
    period = request.args.get('period', 'last20')

    if period == 'all':
        return period, None, None, None

    m = re.match(r'^last(\d+)$', period)
    if m:
        return period, None, None, int(m.group(1))

    if period == 'day':
        date_str = request.args.get('date')
        if date_str:
            try:
                day = datetime.strptime(date_str, '%Y-%m-%d')
                since = day.replace(hour=0, minute=0, second=0, microsecond=0,
                                    tzinfo=c.JST)
                return period, since, date_str, None
            except ValueError:
                pass
        now = c.get_now()
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return period, since, now.strftime('%Y-%m-%d'), None

    return 'last20', None, None, 20


def _get_available_chars(battle_type=None):
    """使用キャラ一覧を取得"""
    char_stats = stats.get_character_stats(since_dt=None, battle_type=battle_type)
    return [s['name'] for s in char_stats]


@bp.route('/')
def index():
    mode = request.args.get('mode', 'all')
    bt = mode if mode != 'all' else None
    selected_char = request.args.get('char') or None

    period, since_dt, selected_date, last_n = _parse_period()

    period_stats = stats.get_today_stats(battle_type=bt, since_dt=since_dt,
                                         last_n=last_n, my_character=selected_char)
    if last_n:
        matches = storage.get_matches(limit=last_n, battle_type=bt)
    else:
        matches = storage.get_matches_since(since_dt, battle_type=bt, limit=100)
    if selected_char:
        matches = [m for m in matches if m['my_character'] == selected_char]

    status = sched.get_scheduler_status()
    auth = cfn_auth.is_authenticated()
    char_stats = stats.get_character_stats(since_dt=since_dt, battle_type=bt,
                                           last_n=last_n)
    opp_stats = stats.get_opponent_stats(since_dt=since_dt, battle_type=bt,
                                         last_n=last_n)
    if selected_char:
        opp_stats = []  # キャラフィルター時は matchup stats でカバー
    lp_history = stats.get_lp_mr_history(limit=50, battle_type=bt)

    custom_last_n = last_n if period not in _PRESET_PERIODS and last_n else None
    available_chars = _get_available_chars(battle_type=bt)

    return render_template('dashboard.html',
                           matches=matches, today=period_stats,
                           status=status, auth=auth,
                           char_stats=char_stats,
                           opp_stats=opp_stats,
                           lp_history=lp_history,
                           current_mode=mode,
                           battle_modes=BATTLE_MODES,
                           current_period=period,
                           period_choices=PERIOD_CHOICES,
                           selected_date=selected_date,
                           custom_last_n=custom_last_n,
                           selected_char=selected_char,
                           available_chars=available_chars)
