from services import storage
from services.stats_aggregates import _calc_streak
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

    # 読み取り API では DB を更新しない。挿入時の check_streak_record に一本化する。
    saved_win = storage.get_streak_record('best_win')
    saved_lose = storage.get_streak_record('worst_lose')

    if saved_win:
        best_win = max(best_win, saved_win['value'])
    if saved_lose:
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
