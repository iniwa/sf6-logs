from flask import Blueprint, render_template

from services import storage, stats
from services import scheduler as sched
from services import cfn_auth

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    matches = storage.get_matches(limit=50)
    today = stats.get_today_stats()
    status = sched.get_scheduler_status()
    auth = cfn_auth.is_authenticated()
    char_stats = stats.get_character_stats()
    matchup_stats = stats.get_matchup_stats()
    opp_stats = stats.get_opponent_stats()
    lp_history = stats.get_lp_mr_history(limit=50)
    return render_template('dashboard.html',
                           matches=matches, today=today,
                           status=status, auth=auth,
                           char_stats=char_stats,
                           matchup_stats=matchup_stats,
                           opp_stats=opp_stats,
                           lp_history=lp_history)
