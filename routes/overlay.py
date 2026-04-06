from flask import Blueprint, render_template

from services import stats

bp = Blueprint('overlay', __name__)


@bp.route('/overlay')
def full():
    today = stats.get_today_stats()
    recent = stats.get_recent_results(count=10)
    return render_template('overlay/full.html', today=today, recent=recent)
