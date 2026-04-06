from flask import Blueprint, jsonify, request

from services import storage, stats, cfn_auth
from services import scheduler as sched

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/status')
def status():
    return jsonify({
        'scheduler': sched.get_scheduler_status(),
        'authenticated': cfn_auth.is_authenticated(),
        'mock_mode': storage.get_config('mock_mode', 'true') == 'true',
    })


@bp.route('/stats/today')
def stats_today():
    return jsonify(stats.get_today_stats())


@bp.route('/stats/session')
def stats_session():
    return jsonify(stats.get_session_stats())


@bp.route('/matches')
def matches():
    limit = request.args.get('limit', 20, type=int)
    battle_type = request.args.get('type')
    return jsonify(storage.get_matches(limit=limit, battle_type=battle_type))
