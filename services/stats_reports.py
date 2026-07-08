from collections import defaultdict
from datetime import datetime, timedelta

import config as c
from services import storage
from services.stats_aggregates import (
    _latest_lp,
    _latest_mr,
    get_current_lp,
    get_session_stats,
    is_master,
)
from services.stats_records import _compute_all_streaks
# --- ハイライトサマリー ---

def get_highlight_stats(battle_type=None):
    """配信ハイライト用のサマリーデータを返す"""
    session = storage.get_current_session()
    if session:
        since = datetime.fromisoformat(session['started_at'])
        matches = storage.get_matches_since(since, battle_type=battle_type)
        started_at = session['started_at']
    else:
        since = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
        matches = storage.get_matches_since(since, battle_type=battle_type)
        started_at = since.isoformat()

    wins = sum(1 for m in matches if m['result'] == 'win')
    losses = sum(1 for m in matches if m['result'] == 'lose')
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total > 0 else 0.0

    # LP/MR delta
    lp_start = mr_start = lp_end = mr_end = None
    if matches:
        oldest = matches[-1]
        latest = matches[0]
        lp_start = oldest.get('lp_before')
        mr_start = oldest.get('mr_before')
        lp_end = _latest_lp(latest)
        mr_end = _latest_mr(latest)

    # Best streak during session
    best_win_streak = 0
    best_lose_streak = 0
    if matches:
        asc_matches = list(reversed(matches))
        current_type = None
        current_count = 0
        for m in asc_matches:
            if m['result'] == current_type:
                current_count += 1
            else:
                current_type = m['result']
                current_count = 1
            if current_type == 'win' and current_count > best_win_streak:
                best_win_streak = current_count
            elif current_type == 'lose' and current_count > best_lose_streak:
                best_lose_streak = current_count

    # Most-faced opponent character
    opp_chars = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        if m['result'] == 'win':
            opp_chars[m['opp_character']]['wins'] += 1
        else:
            opp_chars[m['opp_character']]['losses'] += 1
    most_faced_opp = None
    if opp_chars:
        name = max(opp_chars, key=lambda k: opp_chars[k]['wins'] + opp_chars[k]['losses'])
        t = opp_chars[name]['wins'] + opp_chars[name]['losses']
        most_faced_opp = {
            'name': name, 'count': t,
            'wins': opp_chars[name]['wins'], 'losses': opp_chars[name]['losses'],
            'winrate': round(opp_chars[name]['wins'] / t * 100, 1) if t > 0 else 0.0,
        }

    # Most-used character
    my_chars = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        if m['result'] == 'win':
            my_chars[m['my_character']]['wins'] += 1
        else:
            my_chars[m['my_character']]['losses'] += 1
    most_used_char = None
    if my_chars:
        name = max(my_chars, key=lambda k: my_chars[k]['wins'] + my_chars[k]['losses'])
        t = my_chars[name]['wins'] + my_chars[name]['losses']
        most_used_char = {
            'name': name, 'count': t,
            'wins': my_chars[name]['wins'], 'losses': my_chars[name]['losses'],
            'winrate': round(my_chars[name]['wins'] / t * 100, 1) if t > 0 else 0.0,
        }

    return {
        'wins': wins, 'losses': losses, 'total': total, 'winrate': winrate,
        'lp_start': lp_start, 'lp_end': lp_end,
        'lp_delta': (lp_end - lp_start) if lp_start is not None and lp_end is not None else None,
        'mr_start': mr_start, 'mr_end': mr_end,
        'mr_delta': (mr_end - mr_start) if mr_start is not None and mr_end is not None else None,
        'is_master': is_master(),
        'best_win_streak': best_win_streak, 'best_lose_streak': best_lose_streak,
        'most_faced_opp': most_faced_opp, 'most_used_char': most_used_char,
        'started_at': started_at, 'has_session': session is not None,
    }


# --- 曜日×時間帯クロス分析 ---

def get_day_hour_stats(battle_type=None, my_character=None):
    """曜日(0=Mon..6=Sun) × 時間帯(0-23) の勝率マトリクスを返す"""
    matches = storage.get_all_matches(battle_type=battle_type)
    if my_character:
        matches = [m for m in matches if m['my_character'] == my_character]

    grid = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    for m in matches:
        try:
            dt = datetime.fromisoformat(m['played_at'])
            dow = dt.weekday()
            hour = dt.hour
        except (TypeError, ValueError):
            continue
        if m['result'] == 'win':
            grid[dow][hour]['wins'] += 1
        else:
            grid[dow][hour]['losses'] += 1

    result = []
    for dow in range(7):
        row = []
        for h in range(24):
            cell = grid[dow][h]
            total = cell['wins'] + cell['losses']
            winrate = round(cell['wins'] / total * 100, 1) if total > 0 else None
            row.append({
                'wins': cell['wins'], 'losses': cell['losses'],
                'total': total, 'winrate': winrate,
            })
        result.append(row)
    return result


# --- 連戦パフォーマンス劣化分析 ---

def get_session_fatigue(battle_type=None, my_character=None):
    """セッション内の試合番号ごとの累積勝率を返す"""
    sessions = storage.get_all_sessions(limit=200)
    game_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})

    for session in sessions:
        started = session['started_at']
        ended = session.get('ended_at')
        matches = storage.get_matches_between(started, ended,
                                              battle_type=battle_type)
        if my_character:
            matches = [m for m in matches if m['my_character'] == my_character]
        matches.reverse()  # 時系列昇順
        for i, m in enumerate(matches):
            game_num = i + 1
            if m['result'] == 'win':
                game_stats[game_num]['wins'] += 1
            else:
                game_stats[game_num]['losses'] += 1

    if not game_stats:
        return []

    result = []
    for i in range(1, min(max(game_stats.keys()) + 1, 51)):
        s = game_stats.get(i, {'wins': 0, 'losses': 0})
        total = s['wins'] + s['losses']
        if total < 2:
            break
        result.append({
            'game_num': i,
            'wins': s['wins'], 'losses': s['losses'],
            'total': total,
            'winrate': round(s['wins'] / total * 100, 1),
        })
    return result


# --- パーソナルレコード ---

def get_personal_records(battle_type=None):
    """歴代パーソナルレコードを返す"""
    matches = storage.get_all_matches(battle_type=battle_type)
    if not matches:
        return {}

    total = len(matches)
    wins = sum(1 for m in matches if m['result'] == 'win')

    best_mr = 0
    for m in matches:
        mr = m.get('mr_after')
        if mr and mr > best_mr:
            best_mr = mr

    streaks = _compute_all_streaks(matches)
    best_win = max((cnt for res, cnt in streaks if res == 'win'), default=0)
    worst_lose = max((cnt for res, cnt in streaks if res == 'lose'), default=0)

    daily = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total': 0})
    for m in matches:
        try:
            day = m['played_at'][:10]
        except (TypeError, IndexError):
            continue
        daily[day]['total'] += 1
        if m['result'] == 'win':
            daily[day]['wins'] += 1
        else:
            daily[day]['losses'] += 1

    best_day_wins = max(daily.items(), key=lambda x: x[1]['wins'])
    most_games_day = max(daily.items(), key=lambda x: x[1]['total'])
    qualified = [(d, v) for d, v in daily.items() if v['total'] >= 5]
    best_day_wr = max(qualified,
                      key=lambda x: x[1]['wins'] / x[1]['total'],
                      default=None) if qualified else None

    result = {
        'total_matches': total,
        'total_wins': wins,
        'total_winrate': round(wins / total * 100, 1) if total > 0 else 0,
        'best_mr': best_mr if best_mr > 0 else None,
        'best_win_streak': best_win,
        'worst_lose_streak': worst_lose,
        'best_day_wins': {
            'date': best_day_wins[0],
            'wins': best_day_wins[1]['wins'],
            'total': best_day_wins[1]['total'],
        },
        'most_games_day': {
            'date': most_games_day[0],
            'total': most_games_day[1]['total'],
            'wins': most_games_day[1]['wins'],
            'losses': most_games_day[1]['losses'],
        },
    }
    if best_day_wr:
        d, v = best_day_wr
        result['best_day_winrate'] = {
            'date': d,
            'winrate': round(v['wins'] / v['total'] * 100, 1),
            'total': v['total'],
        }
    return result


# --- 週間/月間レポート ---

def get_report_data(range_type='weekly', battle_type=None):
    """週間 or 月間のレポートデータを返す。
    range_type: 'weekly' (過去7日) or 'monthly' (過去30日)
    """
    now = c.get_now()
    if range_type == 'monthly':
        since = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0,
                                                   microsecond=0)
        period_label = '過去30日間'
    else:
        since = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0,
                                                  microsecond=0)
        period_label = '過去7日間'

    matches = storage.get_matches_since(since, battle_type=battle_type)
    if not matches:
        return {'period': period_label, 'since': since.isoformat(),
                'total': 0, 'wins': 0, 'losses': 0}

    wins = sum(1 for m in matches if m['result'] == 'win')
    losses = len(matches) - wins
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total > 0 else 0

    # 日別集計
    daily = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        try:
            day = m['played_at'][:10]
        except (TypeError, IndexError):
            continue
        if m['result'] == 'win':
            daily[day]['wins'] += 1
        else:
            daily[day]['losses'] += 1
    daily_list = []
    for d in sorted(daily.keys()):
        dw = daily[d]['wins']
        dl = daily[d]['losses']
        dt = dw + dl
        daily_list.append({
            'date': d, 'wins': dw, 'losses': dl, 'total': dt,
            'winrate': round(dw / dt * 100, 1) if dt > 0 else 0,
        })

    # キャラ別
    char_data = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        c_name = m['my_character']
        if m['result'] == 'win':
            char_data[c_name]['wins'] += 1
        else:
            char_data[c_name]['losses'] += 1
    char_list = []
    for name in sorted(char_data.keys()):
        cw = char_data[name]['wins']
        cl = char_data[name]['losses']
        ct = cw + cl
        char_list.append({
            'name': name, 'wins': cw, 'losses': cl, 'total': ct,
            'winrate': round(cw / ct * 100, 1) if ct > 0 else 0,
        })

    # 対戦相手キャラ別
    opp_data = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        opp_c = m['opp_character']
        if m['result'] == 'win':
            opp_data[opp_c]['wins'] += 1
        else:
            opp_data[opp_c]['losses'] += 1
    opp_list = []
    for name in sorted(opp_data.keys()):
        ow = opp_data[name]['wins']
        ol = opp_data[name]['losses']
        ot = ow + ol
        opp_list.append({
            'name': name, 'wins': ow, 'losses': ol, 'total': ot,
            'winrate': round(ow / ot * 100, 1) if ot > 0 else 0,
        })

    # LP/MR 変動
    oldest = matches[-1]  # oldest (matches are desc)
    latest = matches[0]
    lp_start = oldest.get('lp_before')
    lp_end = _latest_lp(latest)
    mr_start = oldest.get('mr_before')
    mr_end = _latest_mr(latest)

    # ストリーク
    asc = list(reversed(matches))
    streaks = _compute_all_streaks(asc)
    best_win = max((cnt for res, cnt in streaks if res == 'win'), default=0)
    worst_lose = max((cnt for res, cnt in streaks if res == 'lose'), default=0)

    # 最もプレイした日
    best_day = max(daily_list, key=lambda x: x['total']) if daily_list else None
    best_wr_day = None
    qualified = [d for d in daily_list if d['total'] >= 5]
    if qualified:
        best_wr_day = max(qualified, key=lambda x: x['winrate'])

    return {
        'period': period_label,
        'since': since.isoformat(),
        'total': total, 'wins': wins, 'losses': losses, 'winrate': winrate,
        'daily': daily_list,
        'characters': char_list,
        'opponents': opp_list,
        'lp_start': lp_start, 'lp_end': lp_end,
        'lp_delta': (lp_end - lp_start) if lp_start and lp_end else None,
        'mr_start': mr_start, 'mr_end': mr_end,
        'mr_delta': (mr_end - mr_start) if mr_start and mr_end else None,
        'best_win_streak': best_win, 'worst_lose_streak': worst_lose,
        'best_day': best_day, 'best_winrate_day': best_wr_day,
    }


# --- 目標プログレス ---

def get_goal_progress():
    """目標に対する進捗を返す"""
    goal_type = storage.get_config('goal_type', '')
    goal_value_str = storage.get_config('goal_value', '')
    goal_label = storage.get_config('goal_label', '')

    if not goal_type or not goal_value_str:
        return None

    try:
        goal_value = float(goal_value_str)
    except (ValueError, TypeError):
        return None

    current = None
    if goal_type == 'mr':
        lp_data = get_current_lp()
        current = lp_data.get('mr')
        if not goal_label:
            goal_label = f'MR {int(goal_value)}'
    elif goal_type == 'lp':
        lp_data = get_current_lp()
        current = lp_data.get('lp')
        if not goal_label:
            goal_label = f'LP {int(goal_value)}'
    elif goal_type == 'winrate':
        today = get_session_stats()
        current = today.get('winrate')
        if not goal_label:
            goal_label = f'Win Rate {goal_value}%'

    if current is None:
        return None

    if goal_type == 'winrate':
        progress = min(round(current / goal_value * 100, 1), 100) if goal_value > 0 else 0
    else:
        session = storage.get_current_session()
        if session:
            since = datetime.fromisoformat(session['started_at'])
            matches = storage.get_matches_since(since)
        else:
            since = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
            matches = storage.get_matches_since(since)

        start_val = current
        if matches:
            oldest = matches[-1]
            start_val = oldest.get('mr_before' if goal_type == 'mr' else 'lp_before') or current

        range_total = goal_value - start_val
        if range_total > 0:
            progress = min(round((current - start_val) / range_total * 100, 1), 100)
        elif current >= goal_value:
            progress = 100
        else:
            progress = 0

    return {
        'type': goal_type,
        'target': goal_value,
        'current': current,
        'progress': max(0, progress),
        'label': goal_label,
        'reached': current >= goal_value,
    }
