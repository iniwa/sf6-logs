import json
import queue
import threading

from flask import Blueprint, jsonify, request, Response

from services import storage, stats, cfn_auth
from services import scheduler as sched

bp = Blueprint('api', __name__, url_prefix='/api')

# --- SSE ---
_sse_clients = []
_sse_lock = threading.Lock()


def _notify_clients(match_dict):
    today = stats.get_today_stats()
    data = json.dumps(today, ensure_ascii=False)
    msg = f"event: stats\ndata: {data}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


storage.register_post_insert_hook(_notify_clients)


@bp.route('/status')
def status():
    return jsonify({
        'scheduler': sched.get_scheduler_status(),
        'authenticated': cfn_auth.is_authenticated(),
        'mock_mode': storage.get_config('mock_mode', 'true') == 'true',
    })


@bp.route('/stats/today')
def stats_today():
    mode = request.args.get('mode')
    return jsonify(stats.get_today_stats(battle_type=mode))


@bp.route('/stats/session')
def stats_session():
    mode = request.args.get('mode')
    return jsonify(stats.get_session_stats(battle_type=mode))


@bp.route('/matches')
def matches():
    limit = request.args.get('limit', 20, type=int)
    battle_type = request.args.get('type')
    return jsonify(storage.get_matches(limit=limit, battle_type=battle_type))


@bp.route('/stats/characters')
def stats_characters():
    mode = request.args.get('mode')
    return jsonify(stats.get_character_stats(battle_type=mode))


@bp.route('/stats/matchups')
def stats_matchups():
    mode = request.args.get('mode')
    return jsonify(stats.get_matchup_stats(battle_type=mode))


@bp.route('/stats/opponents')
def stats_opponents():
    mode = request.args.get('mode')
    return jsonify(stats.get_opponent_stats(battle_type=mode))


@bp.route('/stats/lp-history')
def stats_lp_history():
    limit = request.args.get('limit', 50, type=int)
    mode = request.args.get('mode')
    return jsonify(stats.get_lp_mr_history(limit=limit, battle_type=mode))


@bp.route('/stream')
def stream():
    q = queue.Queue(maxsize=50)
    with _sse_lock:
        _sse_clients.append(q)

    def generate():
        try:
            # 接続時に現在の stats を送信
            today = stats.get_today_stats()
            yield f"event: stats\ndata: {json.dumps(today, ensure_ascii=False)}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
