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
    return render_template('dashboard.html',
                           matches=matches, today=today,
                           status=status, auth=auth)
