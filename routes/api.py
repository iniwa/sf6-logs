import json
import queue
import re
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

    # ポップアップ通知設定をチェック
    popup_match = storage.get_config('popup_match_result', '1') == '1'
    popup_rank = storage.get_config('popup_rank_change', '1') == '1'
    popup_mr_ms = storage.get_config('popup_mr_milestone', '1') == '1'
    popup_streak = storage.get_config('popup_streak_record', '1') == '1'
    popup_best_mr = storage.get_config('popup_best_mr', '1') == '1'

    # 最新マッチ情報を event: match で送信
    match_msg = ""
    if popup_match:
        matches = storage.get_matches(limit=1)
        if matches:
            match_msg = f"event: match\ndata: {json.dumps(matches[0], ensure_ascii=False)}\n\n"

    # マイルストーン通知
    milestone_msgs = []
    milestones = stats.check_milestone(match_dict)
    for ms in milestones:
        if ms['type'] == 'rank_change' and not popup_rank:
            continue
        if ms['type'] in ('mr_milestone', 'master_reached') and not popup_mr_ms:
            continue
        if ms['type'] == 'best_mr' and not popup_best_mr:
            continue
        milestone_msgs.append(
            f"event: milestone\ndata: {json.dumps(ms, ensure_ascii=False)}\n\n"
        )

    # ストリーク記録更新チェック
    streak_msg = ""
    if popup_streak:
        streak_record = stats.check_streak_record(match_dict)
        if streak_record:
            streak_msg = f"event: milestone\ndata: {json.dumps(streak_record, ensure_ascii=False)}\n\n"

    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(stats_msg)
                if match_msg:
                    q.put_nowait(match_msg)
                for ms_msg in milestone_msgs:
                    q.put_nowait(ms_msg)
                if streak_msg:
                    q.put_nowait(streak_msg)
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
    """API 用の期間パラメータを解析して (since_dt, last_n) を返す"""
    period = request.args.get('period')
    if not period:
        return stats._UNSET, None  # デフォルト（今日）
    if period == 'all':
        return None, None

    # lastN パターン
    m = re.match(r'^last(\d+)$', period)
    if m:
        return None, int(m.group(1))

    if period == 'day':
        date_str = request.args.get('date')
        if date_str:
            try:
                day = datetime.strptime(date_str, '%Y-%m-%d')
                return day.replace(hour=0, minute=0, second=0, microsecond=0,
                                   tzinfo=c.JST), None
            except ValueError:
                pass
        return c.get_now().replace(hour=0, minute=0, second=0, microsecond=0), None

    return stats._UNSET, None


@bp.route('/stats/today')
def stats_today():
    mode = request.args.get('mode')
    char = request.args.get('char')
    since_dt, last_n = _parse_api_period()
    return jsonify(stats.get_today_stats(battle_type=mode, since_dt=since_dt,
                                         last_n=last_n, my_character=char))


@bp.route('/stats/session')
def stats_session():
    mode = request.args.get('mode')
    char = request.args.get('char')
    return jsonify(stats.get_session_stats(battle_type=mode, my_character=char))


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
    since_dt, last_n = _parse_api_period()
    return jsonify(stats.get_lp_mr_history(limit=limit, battle_type=mode,
                                           since_dt=since_dt, last_n=last_n))


@bp.route('/stats/calendar')
def stats_calendar():
    days = request.args.get('days', 90, type=int)
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    return jsonify(stats.get_calendar_data(days=days, battle_type=bt))


@bp.route('/stats/hourly')
def stats_hourly():
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    since_dt, last_n = _parse_api_period()
    return jsonify(stats.get_hourly_stats(since_dt=since_dt, battle_type=bt,
                                          last_n=last_n))


@bp.route('/stats/streaks')
def stats_streaks():
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    return jsonify(stats.get_best_streaks(battle_type=bt))


@bp.route('/stats/rematches')
def stats_rematches():
    limit = request.args.get('limit', 50, type=int)
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    since_dt, last_n = _parse_api_period()
    return jsonify(stats.detect_rematches(limit=limit, battle_type=bt,
                                          since_dt=since_dt, last_n=last_n))


@bp.route('/stats/heatmap')
def stats_heatmap():
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    since_dt, last_n = _parse_api_period()
    return jsonify(stats.get_matchup_heatmap(since_dt=since_dt, battle_type=bt,
                                             last_n=last_n))


@bp.route('/stats/rolling-winrate')
def stats_rolling_winrate():
    window = request.args.get('window', 10, type=int)
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    return jsonify(stats.get_rolling_winrate(window=window, battle_type=bt))


@bp.route('/goal')
def goal_get():
    progress = stats.get_goal_progress()
    if progress is None:
        return jsonify({'active': False})
    return jsonify({'active': True, **progress})


@bp.route('/stats/highlight')
def stats_highlight():
    mode = request.args.get('mode')
    bt = mode if mode and mode != 'all' else None
    return jsonify(stats.get_highlight_stats(battle_type=bt))


@bp.route('/sessions')
def sessions_list():
    sessions = storage.get_all_sessions(limit=50)
    result = []
    for s in sessions:
        started = datetime.fromisoformat(s['started_at'])
        ended_str = s.get('ended_at')
        ended = datetime.fromisoformat(ended_str) if ended_str else None
        matches = storage.get_matches_between(
            s['started_at'], ended_str
        )
        wins = sum(1 for m in matches if m['result'] == 'win')
        losses = len(matches) - wins
        total = wins + losses
        result.append({
            **s,
            'wins': wins,
            'losses': losses,
            'total': total,
            'winrate': round(wins / total * 100, 1) if total > 0 else 0.0,
        })
    return jsonify(result)


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
