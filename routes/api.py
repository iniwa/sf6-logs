import json
import queue
import threading

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, Response

import config as c
from services import storage, stats, cfn_auth
from services import scheduler as sched

bp = Blueprint('api', __name__, url_prefix='/api')

# --- SSE ---
_sse_clients = []
_sse_lock = threading.Lock()


def _notify_clients(match_dict):
    today = stats.get_session_stats()
    stats_msg = f"event: stats\ndata: {json.dumps(today, ensure_ascii=False)}\n\n"

    # 最新マッチ情報を event: match で送信
    matches = storage.get_matches(limit=1)
    match_msg = ""
    if matches:
        match_msg = f"event: match\ndata: {json.dumps(matches[0], ensure_ascii=False)}\n\n"

    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(stats_msg)
                if match_msg:
                    q.put_nowait(match_msg)
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


def _parse_api_period():
    """API 用の期間パラメータを解析して since_dt を返す"""
    period = request.args.get('period')
    if not period:
        return stats._UNSET  # デフォルト（今日）
    if period == 'all':
        return None
    if period == 'day':
        date_str = request.args.get('date')
        if date_str:
            try:
                day = datetime.strptime(date_str, '%Y-%m-%d')
                return day.replace(hour=0, minute=0, second=0, microsecond=0,
                                   tzinfo=c.JST)
            except ValueError:
                pass
        return c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
    hours_map = {'24h': 24, '8h': 8, '1h': 1}
    hours = hours_map.get(period, 24)
    return c.get_now() - timedelta(hours=hours)


@bp.route('/stats/today')
def stats_today():
    mode = request.args.get('mode')
    since_dt = _parse_api_period()
    return jsonify(stats.get_today_stats(battle_type=mode, since_dt=since_dt))


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
            today = stats.get_session_stats()
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
