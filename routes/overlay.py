from flask import Blueprint, render_template, request

from services import stats, storage

bp = Blueprint('overlay', __name__)

VALID_THEMES = ('dark', 'sf6')
VALID_SIZES = ('small', 'medium', 'large')
VALID_LAYOUTS = ('vertical', 'horizontal')
VALID_POSITIONS = ('right', 'left')

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
    pos = request.args.get('pos', 'right')
    if pos not in VALID_POSITIONS:
        pos = 'right'
    mode = request.args.get('mode', 'all')
    if mode not in VALID_MODES:
        mode = 'all'
    bt = mode if mode != 'all' else None

    # Character filter
    char_param = request.args.get('char', '')
    char_filter = None
    if char_param == 'auto':
        recent_match = storage.get_matches(limit=1, battle_type=bt)
        if recent_match:
            char_filter = recent_match[0]['my_character']
    elif char_param:
        char_filter = char_param

    today = stats.get_session_stats(battle_type=bt, my_character=char_filter)
    recent = stats.get_recent_results(count=10, battle_type=bt, my_character=char_filter)

    # Goal progress bar
    goal = None
    if request.args.get('goal', '0') == '1':
        goal = stats.get_goal_progress()

    return {
        'theme': theme,
        'size': size,
        'layout': layout,
        'anim': anim,
        'streak': streak,
        'pos': pos,
        'mode': mode,
        'char_filter': char_filter or '',
        'goal': goal,
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


@bp.route('/overlay/highlight')
def highlight():
    ctx = _overlay_context()
    bt = ctx['mode'] if ctx['mode'] != 'all' else None
    highlight_data = stats.get_highlight_stats(battle_type=bt)
    return render_template('overlay/highlight.html', **ctx, highlight=highlight_data)


@bp.route('/overlay/preview')
def preview():
    return render_template('overlay/preview.html')
