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
    ('all', 'All'),
    ('day', '1 Day'),
    ('24h', '24h'),
    ('8h', '8h'),
    ('1h', '1h'),
]


def _parse_period():
    """期間パラメータから since_dt を計算。None は全期間を意味する。"""
    period = request.args.get('period', 'day')
    now = c.get_now()

    if period == 'all':
        return period, None, None

    if period == 'day':
        date_str = request.args.get('date')
        if date_str:
            try:
                day = datetime.strptime(date_str, '%Y-%m-%d')
                since = day.replace(hour=0, minute=0, second=0, microsecond=0,
                                    tzinfo=c.JST)
                return period, since, date_str
            except ValueError:
                pass
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return period, since, now.strftime('%Y-%m-%d')

    hours_map = {'24h': 24, '8h': 8, '1h': 1}
    hours = hours_map.get(period, 24)
    since = now - timedelta(hours=hours)
    return period, since, None


@bp.route('/')
def index():
    mode = request.args.get('mode', 'all')
    bt = mode if mode != 'all' else None

    period, since_dt, selected_date = _parse_period()

    period_stats = stats.get_today_stats(battle_type=bt, since_dt=since_dt)
    matches = storage.get_matches_since(since_dt, battle_type=bt, limit=100)
    status = sched.get_scheduler_status()
    auth = cfn_auth.is_authenticated()
    char_stats = stats.get_character_stats(since_dt=since_dt, battle_type=bt)
    matchup_stats = stats.get_matchup_stats(since_dt=since_dt, battle_type=bt)
    opp_stats = stats.get_opponent_stats(since_dt=since_dt, battle_type=bt)
    lp_history = stats.get_lp_mr_history(limit=50, battle_type=bt)
    return render_template('dashboard.html',
                           matches=matches, today=period_stats,
                           status=status, auth=auth,
                           char_stats=char_stats,
                           matchup_stats=matchup_stats,
                           opp_stats=opp_stats,
                           lp_history=lp_history,
                           current_mode=mode,
                           battle_modes=BATTLE_MODES,
                           current_period=period,
                           period_choices=PERIOD_CHOICES,
                           selected_date=selected_date)
