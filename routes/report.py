from flask import Blueprint, render_template, request

from services import stats

bp = Blueprint('report', __name__)

BATTLE_MODES = [
    ('all', 'All'),
    ('ranked', 'Ranked'),
    ('casual', 'Casual'),
    ('battle_hub', 'Battle Hub'),
    ('custom', 'Custom'),
]


@bp.route('/report')
def index():
    range_type = request.args.get('range', 'weekly')
    if range_type not in ('weekly', 'monthly'):
        range_type = 'weekly'
    mode = request.args.get('mode', 'all')
    bt = mode if mode != 'all' else None

    data = stats.get_report_data(range_type=range_type, battle_type=bt)
    records = stats.get_personal_records(battle_type=bt)

    return render_template('report.html',
                           data=data,
                           records=records,
                           current_range=range_type,
                           current_mode=mode,
                           battle_modes=BATTLE_MODES)
