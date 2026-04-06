from flask import Blueprint, render_template, request

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


@bp.route('/')
def index():
    mode = request.args.get('mode', 'all')
    bt = mode if mode != 'all' else None

    matches = storage.get_matches(limit=50, battle_type=bt)
    today = stats.get_today_stats(battle_type=bt)
    status = sched.get_scheduler_status()
    auth = cfn_auth.is_authenticated()
    char_stats = stats.get_character_stats(battle_type=bt)
    matchup_stats = stats.get_matchup_stats(battle_type=bt)
    opp_stats = stats.get_opponent_stats(battle_type=bt)
    lp_history = stats.get_lp_mr_history(limit=50, battle_type=bt)
    return render_template('dashboard.html',
                           matches=matches, today=today,
                           status=status, auth=auth,
                           char_stats=char_stats,
                           matchup_stats=matchup_stats,
                           opp_stats=opp_stats,
                           lp_history=lp_history,
                           current_mode=mode,
                           battle_modes=BATTLE_MODES)
