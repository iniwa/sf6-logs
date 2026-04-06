from flask import Blueprint, render_template, request

from services import stats

bp = Blueprint('overlay', __name__)

VALID_THEMES = ('dark', 'sf6')
VALID_SIZES = ('small', 'medium', 'large')


def _overlay_context():
    theme = request.args.get('theme', 'dark')
    if theme not in VALID_THEMES:
        theme = 'dark'
    size = request.args.get('size', 'medium')
    if size not in VALID_SIZES:
        size = 'medium'
    today = stats.get_today_stats()
    recent = stats.get_recent_results(count=10)
    return {
        'theme': theme,
        'size': size,
        'today': today,
        'recent': recent,
    }


@bp.route('/overlay')
def full():
    return render_template('overlay/full.html', **_overlay_context())


@bp.route('/overlay/record')
def record():
    return render_template('overlay/record.html', **_overlay_context())


@bp.route('/overlay/lp')
def lp():
    return render_template('overlay/lp.html', **_overlay_context())


@bp.route('/overlay/history')
def history():
    return render_template('overlay/history.html', **_overlay_context())
