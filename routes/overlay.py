from flask import Blueprint, render_template, request

from services import stats

bp = Blueprint('overlay', __name__)

VALID_THEMES = ('dark', 'sf6')
VALID_SIZES = ('small', 'medium', 'large')
VALID_LAYOUTS = ('vertical', 'horizontal')

VALID_MODES = ('all', 'ranked', 'casual', 'battle_hub', 'custom')


def _overlay_context():
    theme = request.args.get('theme', 'dark')
    if theme not in VALID_THEMES:
        theme = 'dark'
    size = request.args.get('size', 'medium')
    if size not in VALID_SIZES:
        size = 'medium'
    layout = request.args.get('layout', 'vertical')
    if layout not in VALID_LAYOUTS:
        layout = 'vertical'
    anim = request.args.get('anim', '1') != '0'
    streak = request.args.get('streak', '1') != '0'
    mode = request.args.get('mode', 'all')
    if mode not in VALID_MODES:
        mode = 'all'
    bt = mode if mode != 'all' else None
    today = stats.get_today_stats(battle_type=bt)
    recent = stats.get_recent_results(count=10, battle_type=bt)
    return {
        'theme': theme,
        'size': size,
        'layout': layout,
        'anim': anim,
        'streak': streak,
        'mode': mode,
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


@bp.route('/overlay/popup')
def popup():
    return render_template('overlay/popup.html', **_overlay_context())


@bp.route('/overlay/preview')
def preview():
    return render_template('overlay/preview.html')
