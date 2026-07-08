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


UNSET = object()
_UNSET = UNSET


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

def get_calendar_data(days=90, battle_type=None, year=None):
    """日別勝率データを返す。year 指定時はその年の 1/1〜12/31 (or 今日) を返す"""
    now = c.get_now()
    if year:
        since = datetime(year, 1, 1, tzinfo=c.JST)
        if year == now.year:
            end = now
        else:
            end = datetime(year, 12, 31, tzinfo=c.JST)
        days = (end.date() - since.date()).days + 1
    else:
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


# --- 再戦検知 ---

_REMATCH_MIN_COUNT = 4


def detect_rematches(limit=50, battle_type=None, since_dt=_UNSET, last_n=None):
    """連続で同じ相手と対戦している箇所を検知。
    SF6 の標準リマッチは 2先取 (最大 3 戦) なので、3 戦までは通常の再戦とみなし、
    4 戦以上続いた場合のみ REMATCH として扱う。"""
    if last_n:
        matches = storage.get_matches(limit=last_n, battle_type=battle_type)
    elif since_dt is not _UNSET and since_dt is not None:
        matches = storage.get_matches_since(since_dt, battle_type=battle_type)
    else:
        matches = storage.get_matches(limit=limit, battle_type=battle_type)
    if len(matches) < _REMATCH_MIN_COUNT:
        return []

    groups = []
    current_group = [matches[0]]

    def _flush(group):
        if len(group) >= _REMATCH_MIN_COUNT:
            wins = sum(1 for x in group if x['result'] == 'win')
            losses = len(group) - wins
            groups.append({
                'opp_name': group[0]['opp_name'],
                'opp_character': group[0]['opp_character'],
                'count': len(group),
                'wins': wins,
                'losses': losses,
                'match_ids': [x['id'] for x in group],
            })

    for m in matches[1:]:
        if m['opp_name'] == current_group[0]['opp_name']:
            current_group.append(m)
        else:
            _flush(current_group)
            current_group = [m]

    _flush(current_group)

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
