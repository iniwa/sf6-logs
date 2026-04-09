from collections import defaultdict
from datetime import datetime, timedelta

import config as c
from services import storage


def _latest_mr(match):
    """マッチから最新の MR を取得 (after 優先、なければ before)"""
    return match.get('mr_after') or match.get('mr_before')


def _latest_lp(match):
    """マッチから最新の LP を取得 (after 優先、なければ before)"""
    return match.get('lp_after') or match.get('lp_before')


def is_master():
    """最新マッチに MR があれば MASTER ランク到達と判定"""
    matches = storage.get_matches(limit=1)
    if matches and _latest_mr(matches[0]) is not None:
        return True
    return False


def _calc_streak(matches):
    """先頭（最新）から連続する同一結果をカウント。正=連勝, 負=連敗, 0=なし"""
    if not matches:
        return 0
    first_result = matches[0]['result']
    count = 0
    for m in matches:
        if m['result'] == first_result:
            count += 1
        else:
            break
    return count if first_result == 'win' else -count


_UNSET = object()


def _fetch_matches(since_dt=_UNSET, battle_type=None, last_n=None):
    """since_dt または last_n でマッチを取得"""
    if last_n:
        return storage.get_matches(limit=last_n, battle_type=battle_type)
    if since_dt is _UNSET:
        since_dt = c.get_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return storage.get_matches_since(since_dt, battle_type=battle_type)


def get_today_stats(battle_type=None, since_dt=_UNSET, last_n=None, my_character=None):
    matches = _fetch_matches(since_dt=since_dt, battle_type=battle_type, last_n=last_n)
    if my_character:
        matches = [m for m in matches if m['my_character'] == my_character]

    wins = sum(1 for m in matches if m['result'] == 'win')
    losses = sum(1 for m in matches if m['result'] == 'lose')
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total > 0 else 0.0

    lp = None
    mr = None
    lp_delta = None
    mr_delta = None
    master = is_master()
    if matches:
        latest = matches[0]
        lp = _latest_lp(latest)
        mr = _latest_mr(latest)
        # 本日最初のマッチの before と最新の値で差分計算
        oldest = matches[-1]
        lp_start = oldest.get('lp_before')
        mr_start = oldest.get('mr_before')
        if lp is not None and lp_start is not None:
            lp_delta = lp - lp_start
        if mr is not None and mr_start is not None:
            mr_delta = mr - mr_start

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'winrate': winrate,
        'lp': lp,
        'mr': mr,
        'lp_delta': lp_delta,
        'mr_delta': mr_delta,
        'is_master': master,
        'streak': _calc_streak(matches),
    }


def get_session_stats(battle_type=None, my_character=None):
    session = storage.get_current_session()
    if not session:
        return get_today_stats(battle_type=battle_type, my_character=my_character)

    since = datetime.fromisoformat(session['started_at'])
    matches = storage.get_matches_since(since, battle_type=battle_type)
    if my_character:
        matches = [m for m in matches if m['my_character'] == my_character]

    wins = sum(1 for m in matches if m['result'] == 'win')
    losses = sum(1 for m in matches if m['result'] == 'lose')
    total = wins + losses
    winrate = round(wins / total * 100, 1) if total > 0 else 0.0

    lp = None
    mr = None
    lp_delta = None
    mr_delta = None
    if matches:
        latest = matches[0]
        lp = _latest_lp(latest)
        mr = _latest_mr(latest)
        oldest = matches[-1]
        lp_start = oldest.get('lp_before')
        mr_start = oldest.get('mr_before')
        if lp is not None and lp_start is not None:
            lp_delta = lp - lp_start
        if mr is not None and mr_start is not None:
            mr_delta = mr - mr_start

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'winrate': winrate,
        'lp': lp,
        'mr': mr,
        'lp_delta': lp_delta,
        'mr_delta': mr_delta,
        'is_master': is_master(),
        'streak': _calc_streak(matches),
        'session_id': session['id'],
        'session_label': session.get('label'),
    }


def get_current_lp():
    matches = storage.get_matches(limit=1)
    if not matches:
        return {'lp': None, 'mr': None, 'is_master': False}
    latest = matches[0]
    mr = _latest_mr(latest)
    return {
        'lp': _latest_lp(latest),
        'mr': mr,
        'is_master': mr is not None,
    }


def get_recent_results(count=10, battle_type=None, my_character=None):
    matches = storage.get_matches(limit=count * 3 if my_character else count, battle_type=battle_type)
    if my_character:
        matches = [m for m in matches if m['my_character'] == my_character][:count]
    return [
        {
            'result': m['result'],
            'my_character': m['my_character'],
            'opp_character': m['opp_character'],
            'opp_name': m['opp_name'],
        }
        for m in matches
    ]


def _aggregate_by(matches, key):
    """key でグループ化して W/L/勝率を集計"""
    buckets = {}
    for m in matches:
        name = m[key]
        if name not in buckets:
            buckets[name] = {'wins': 0, 'losses': 0}
        if m['result'] == 'win':
            buckets[name]['wins'] += 1
        else:
            buckets[name]['losses'] += 1

    results = []
    for name, b in buckets.items():
        total = b['wins'] + b['losses']
        results.append({
            'name': name,
            'wins': b['wins'],
            'losses': b['losses'],
            'total': total,
            'winrate': round(b['wins'] / total * 100, 1) if total > 0 else 0.0,
        })
    results.sort(key=lambda x: x['total'], reverse=True)
    return results


def get_character_stats(since_dt=_UNSET, battle_type=None, last_n=None):
    matches = _fetch_matches(since_dt=since_dt, battle_type=battle_type, last_n=last_n)
    return _aggregate_by(matches, 'my_character')


def get_matchup_stats(since_dt=_UNSET, battle_type=None, last_n=None):
    matches = _fetch_matches(since_dt=since_dt, battle_type=battle_type, last_n=last_n)
    return _aggregate_by(matches, 'opp_character')


def get_opponent_stats(since_dt=_UNSET, battle_type=None, last_n=None):
    matches = _fetch_matches(since_dt=since_dt, battle_type=battle_type, last_n=last_n)
    return _aggregate_by(matches, 'opp_name')


def get_lp_mr_history(limit=50, battle_type=None, since_dt=_UNSET, last_n=None):
    if last_n:
        matches = storage.get_matches(limit=last_n, battle_type=battle_type)
    elif since_dt is not _UNSET and since_dt is not None:
        matches = storage.get_matches_since(since_dt, battle_type=battle_type)
    else:
        matches = storage.get_matches(limit=limit, battle_type=battle_type)
    matches.reverse()  # 時系列昇順
    return [
        {
            'played_at': m['played_at'],
            'lp_after': _latest_lp(m),
            'mr_after': _latest_mr(m),
            'result': m['result'],
        }
        for m in matches
        if _latest_lp(m) is not None or _latest_mr(m) is not None
    ]


# --- カレンダーデータ (日別サマリー) ---

def get_calendar_data(days=90, battle_type=None):
    """過去 N 日間の日別勝率データを返す"""
    now = c.get_now()
    since = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    matches = storage.get_matches_since(since, battle_type=battle_type)

    daily = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        try:
            day = m['played_at'][:10]  # YYYY-MM-DD
        except (TypeError, IndexError):
            continue
        if m['result'] == 'win':
            daily[day]['wins'] += 1
        else:
            daily[day]['losses'] += 1

    result = []
    for i in range(days):
        d = (since + timedelta(days=i)).strftime('%Y-%m-%d')
        data = daily.get(d, {'wins': 0, 'losses': 0})
        total = data['wins'] + data['losses']
        winrate = round(data['wins'] / total * 100, 1) if total > 0 else None
        result.append({
            'date': d,
            'wins': data['wins'],
            'losses': data['losses'],
            'total': total,
            'winrate': winrate,
        })
    return result


# --- 時間帯別パフォーマンス ---

def get_hourly_stats(since_dt=_UNSET, battle_type=None, last_n=None):
    """時間帯別 (0-23時) の勝率を返す"""
    if last_n:
        matches = storage.get_matches(limit=last_n, battle_type=battle_type)
    else:
        if since_dt is _UNSET:
            since_dt = None  # 全期間
        matches = storage.get_matches_since(since_dt, battle_type=battle_type)

    hourly = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for m in matches:
        try:
            hour = int(m['played_at'][11:13])
        except (TypeError, ValueError, IndexError):
            continue
        if m['result'] == 'win':
            hourly[hour]['wins'] += 1
        else:
            hourly[hour]['losses'] += 1

    result = []
    for h in range(24):
        data = hourly.get(h, {'wins': 0, 'losses': 0})
        total = data['wins'] + data['losses']
        winrate = round(data['wins'] / total * 100, 1) if total > 0 else 0.0
        result.append({
            'hour': h,
            'wins': data['wins'],
            'losses': data['losses'],
            'total': total,
            'winrate': winrate,
        })
    return result


# --- 連勝/連敗 記録トラッカー ---

def _compute_all_streaks(matches):
    """全マッチから全てのストリーク区間を抽出 (時系列昇順で渡すこと)"""
    if not matches:
        return []
    streaks = []
    current_result = matches[0]['result']
    count = 1
    for m in matches[1:]:
        if m['result'] == current_result:
            count += 1
        else:
            streaks.append((current_result, count))
            current_result = m['result']
            count = 1
    streaks.append((current_result, count))
    return streaks


def get_best_streaks(battle_type=None):
    """歴代ベスト連勝・ワースト連敗を返す"""
    matches = storage.get_all_matches(battle_type=battle_type)
    streaks = _compute_all_streaks(matches)

    best_win = 0
    worst_lose = 0
    for result, count in streaks:
        if result == 'win' and count > best_win:
            best_win = count
        elif result == 'lose' and count > worst_lose:
            worst_lose = count

    # DB のレコードと比較して更新
    saved_win = storage.get_streak_record('best_win')
    saved_lose = storage.get_streak_record('worst_lose')

    if not saved_win or best_win > saved_win['value']:
        storage.save_streak_record('best_win', best_win)
    elif saved_win:
        best_win = max(best_win, saved_win['value'])

    if not saved_lose or worst_lose > saved_lose['value']:
        storage.save_streak_record('worst_lose', worst_lose)
    elif saved_lose:
        worst_lose = max(worst_lose, saved_lose['value'])

    return {
        'best_win_streak': best_win,
        'worst_lose_streak': worst_lose,
    }


def check_streak_record(match_dict):
    """新マッチ挿入後にストリーク記録更新をチェック。更新があれば通知用データを返す"""
    matches = storage.get_matches(limit=100)  # 最新100件
    if not matches:
        return None

    streak = _calc_streak(matches)
    abs_streak = abs(streak)

    if abs_streak < 3:
        return None

    record_type = 'best_win' if streak > 0 else 'worst_lose'
    saved = storage.get_streak_record(record_type)

    if not saved or abs_streak > saved['value']:
        storage.save_streak_record(record_type, abs_streak)
        return {
            'type': 'streak_record',
            'record_type': record_type,
            'value': abs_streak,
            'label': f'{abs_streak}連勝' if streak > 0 else f'{abs_streak}連敗',
            'is_new_record': True,
        }
    return None


# --- 再戦検知 ---

def detect_rematches(limit=50, battle_type=None, since_dt=_UNSET, last_n=None):
    """連続で同じ相手と対戦している箇所を検知"""
    if last_n:
        matches = storage.get_matches(limit=last_n, battle_type=battle_type)
    elif since_dt is not _UNSET and since_dt is not None:
        matches = storage.get_matches_since(since_dt, battle_type=battle_type)
    else:
        matches = storage.get_matches(limit=limit, battle_type=battle_type)
    if len(matches) < 2:
        return []

    groups = []
    current_group = [matches[0]]

    for m in matches[1:]:
        if m['opp_name'] == current_group[0]['opp_name']:
            current_group.append(m)
        else:
            if len(current_group) >= 2:
                wins = sum(1 for x in current_group if x['result'] == 'win')
                losses = len(current_group) - wins
                groups.append({
                    'opp_name': current_group[0]['opp_name'],
                    'opp_character': current_group[0]['opp_character'],
                    'count': len(current_group),
                    'wins': wins,
                    'losses': losses,
                    'match_ids': [x['id'] for x in current_group],
                })
            current_group = [m]

    if len(current_group) >= 2:
        wins = sum(1 for x in current_group if x['result'] == 'win')
        losses = len(current_group) - wins
        groups.append({
            'opp_name': current_group[0]['opp_name'],
            'opp_character': current_group[0]['opp_character'],
            'count': len(current_group),
            'wins': wins,
            'losses': losses,
            'match_ids': [x['id'] for x in current_group],
        })

    return groups


# --- キャラ別 対キャラ勝率ヒートマップ ---

def get_matchup_heatmap(since_dt=_UNSET, battle_type=None, last_n=None):
    """自キャラ × 相手キャラ の勝率マトリクスを返す"""
    if last_n:
        matches = storage.get_matches(limit=last_n, battle_type=battle_type)
    else:
        if since_dt is _UNSET:
            since_dt = None
        matches = storage.get_matches_since(since_dt, battle_type=battle_type)

    matrix = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
    my_chars = set()
    opp_chars = set()

    for m in matches:
        my_c = m['my_character']
        opp_c = m['opp_character']
        my_chars.add(my_c)
        opp_chars.add(opp_c)
        if m['result'] == 'win':
            matrix[my_c][opp_c]['wins'] += 1
        else:
            matrix[my_c][opp_c]['losses'] += 1

    my_chars = sorted(my_chars)
    opp_chars = sorted(opp_chars)

    data = []
    for my_c in my_chars:
        row = {'my_character': my_c, 'matchups': []}
        for opp_c in opp_chars:
            cell = matrix[my_c][opp_c]
            total = cell['wins'] + cell['losses']
            winrate = round(cell['wins'] / total * 100, 1) if total > 0 else None
            row['matchups'].append({
                'opp_character': opp_c,
                'wins': cell['wins'],
                'losses': cell['losses'],
                'total': total,
                'winrate': winrate,
            })
        data.append(row)

    return {
        'my_characters': my_chars,
        'opp_characters': opp_chars,
        'data': data,
    }


# --- ローリング勝率 ---

def get_rolling_winrate(window=10, battle_type=None):
    """直近からのスライディングウィンドウ勝率を時系列で返す"""
    matches = storage.get_all_matches(battle_type=battle_type)
    if len(matches) < window:
        return []

    result = []
    for i in range(window, len(matches) + 1):
        window_matches = matches[i - window:i]
        wins = sum(1 for m in window_matches if m['result'] == 'win')
        winrate = round(wins / window * 100, 1)
        result.append({
            'index': i,
            'played_at': window_matches[-1]['played_at'],
            'winrate': winrate,
        })
    return result


# --- MR/LP マイルストーン検知 ---

# SF6 ランクしきい値 (LP)
RANK_THRESHOLDS = [
    (25000, 'Diamond 5'),
    (23000, 'Diamond 4'),
    (21000, 'Diamond 3'),
    (19000, 'Diamond 2'),
    (17000, 'Diamond 1'),
    (15000, 'Platinum 5'),
    (13000, 'Platinum 4'),
    (11000, 'Platinum 3'),
    (9000,  'Platinum 2'),
    (7000,  'Platinum 1'),
    (5000,  'Gold 5'),
    (4000,  'Gold 4'),
    (3000,  'Gold 3'),
]

def _mr_milestones_between(low, high):
    """low〜high の間にある 100 刻みの MR マイルストーンを返す"""
    start = (low // 100 + 1) * 100
    return list(range(start, high + 1, 100))


def _mr_tier_label(mr_value):
    """MR 値に対応する MASTER ティア名を返す"""
    return f'{mr_value} MASTER'


def _lp_to_rank(lp):
    if lp is None:
        return None
    for threshold, rank in RANK_THRESHOLDS:
        if lp >= threshold:
            return rank
    return 'Below Gold'


def check_milestone(match_dict):
    """マッチ結果からランク変動・MRマイルストーンを検知"""
    notifications = []

    # LP ランク変動
    lp_before = match_dict.get('lp_before')
    lp_after = match_dict.get('lp_after')
    if lp_before is not None and lp_after is not None:
        rank_before = _lp_to_rank(lp_before)
        rank_after = _lp_to_rank(lp_after)
        if rank_before != rank_after and rank_after:
            promoted = lp_after > lp_before
            notifications.append({
                'type': 'rank_change',
                'rank': rank_after,
                'promoted': promoted,
                'label': f'{"昇格" if promoted else "降格"}: {rank_after}',
            })

    # MR マイルストーン (100 刻み、上限なし)
    mr_before = match_dict.get('mr_before')
    mr_after = match_dict.get('mr_after')
    if mr_before is not None and mr_after is not None:
        if mr_after > mr_before:
            for ms in _mr_milestones_between(mr_before, mr_after):
                notifications.append({
                    'type': 'mr_milestone',
                    'value': ms,
                    'label': f'{_mr_tier_label(ms)} 到達!',
                })
        elif mr_after < mr_before:
            for ms in _mr_milestones_between(mr_after, mr_before):
                notifications.append({
                    'type': 'mr_milestone',
                    'value': ms,
                    'label': f'{_mr_tier_label(ms)} を下回りました',
                    'down': True,
                })

    # MASTER 到達
    if mr_after is not None and mr_before is None and lp_before is not None:
        notifications.append({
            'type': 'master_reached',
            'label': 'MASTER ランク到達!',
        })

    # 最高 MR 更新
    if mr_after is not None:
        best_mr_str = storage.get_config('best_mr')
        best_mr = int(best_mr_str) if best_mr_str else 0
        if mr_after > best_mr:
            storage.set_config('best_mr', str(mr_after))
            if best_mr > 0:  # 初回記録時は通知しない
                notifications.append({
                    'type': 'best_mr',
                    'value': mr_after,
                    'label': f'最高 MR 更新! MR {mr_after}',
                })

    return notifications


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
