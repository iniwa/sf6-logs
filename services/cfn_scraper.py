import json
import random
import uuid
from datetime import datetime, timedelta

import config as c
from services import storage
from services.cfn_auth import get_session, get_build_id, build_api_url

# SF6 キャラクターリスト
CHARACTERS = [
    'Ryu', 'Ken', 'Chun-Li', 'Luke', 'Jamie', 'Kimberly',
    'Juri', 'Guile', 'JP', 'Dhalsim', 'Cammy', 'Manon',
    'Dee Jay', 'Lily', 'Zangief', 'Marisa', 'Blanka', 'Honda',
    'Rashid', 'A.K.I.', 'Ed', 'Akuma', 'M. Bison', 'Terry',
    'Mai', 'Elena', 'Gouki',
]

BATTLE_TYPES = ['ranked', 'casual']

# replay_battle_type マッピング
BATTLE_TYPE_MAP = {
    0: 'casual',
    1: 'ranked',
    2: 'battle_hub',
    3: 'battle_hub',
    4: 'custom',
}


def fetch_battle_log(session=None):
    mock_mode = storage.get_config('mock_mode', 'true')
    if mock_mode == 'true':
        return _generate_mock_matches()

    return _fetch_real_battle_log(session)


def _request_battlelog(session, short_id, build_id):
    """バトルログ API にリクエストを送信"""
    url = build_api_url(f'profile/{short_id}/battlelog.json', build_id)
    if not url:
        return None
    try:
        return session.get(url, params={'page': 1}, timeout=15)
    except Exception as e:
        c.log(f'CFN request error: {e}')
        return None


def _fetch_real_battle_log(session):
    """Buckler's Boot Camp からバトルログを取得"""
    short_id = storage.get_config('cfn_user_id')
    if not short_id:
        c.log('CFN user ID (short_id) not configured')
        return []

    if session is None:
        session = get_session()

    build_id = get_build_id(session)
    if not build_id:
        c.log('Failed to get BuildID — cookie may be invalid')
        return []

    resp = _request_battlelog(session, short_id, build_id)
    if resp is None:
        return []

    # BuildID 変更による 404 → リフレッシュして1回リトライ
    if resp.status_code == 404:
        c.log('CFN: 404 — BuildID may be stale, refreshing...')
        new_build_id = get_build_id(session, force_refresh=True)
        if new_build_id and new_build_id != build_id:
            c.log(f'BuildID refreshed: {build_id} → {new_build_id}')
            resp = _request_battlelog(session, short_id, new_build_id)
            if resp is None:
                return []

    # エラーハンドリング
    if resp.status_code == 403:
        c.log('CFN: 403 Unauthorized — cookie expired or invalid')
        return []
    if resp.status_code == 404:
        c.log(f'CFN: 404 Not Found — check short_id: {short_id}')
        return []
    if resp.status_code == 405 and resp.headers.get('x-amzn-waf-action'):
        c.log('CFN: Rate limited by WAF — backing off')
        return []
    if resp.status_code == 503:
        c.log('CFN: 503 Under maintenance')
        return []

    try:
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        c.log(f'CFN fetch error: {e}')
        return []

    return _parse_battle_log(data, short_id)


def _parse_battle_log(data, my_short_id):
    """API レスポンスをデータ契約の形式に変換"""
    page_props = data.get('pageProps', {})
    replay_list = page_props.get('replay_list') or []
    my_short_id = int(my_short_id)

    matches = []
    for replay in replay_list:
        try:
            match = _parse_replay(replay, my_short_id)
            if match:
                matches.append(match)
        except Exception as e:
            replay_id = replay.get('replay_id', 'unknown')
            c.log(f'Failed to parse replay {replay_id}: {e}')

    return matches


def _parse_replay(replay, my_short_id):
    """個別リプレイデータをパース"""
    p1 = replay.get('player1_info', {})
    p2 = replay.get('player2_info', {})

    # 自分がどちらのプレイヤーか判定
    p1_sid = p1.get('player', {}).get('short_id', 0)
    p2_sid = p2.get('player', {}).get('short_id', 0)

    if int(p1_sid) == my_short_id:
        me, opp = p1, p2
    elif int(p2_sid) == my_short_id:
        me, opp = p2, p1
    else:
        # 自分のマッチではない
        return None

    # 勝敗判定: round_results で 0 が 2 つ以上 → 敗北
    round_results = me.get('round_results', [])
    losses = round_results.count(0)
    result = 'lose' if losses >= 2 else 'win'

    # バトルタイプ
    battle_type_id = replay.get('replay_battle_type', -1)
    battle_type = BATTLE_TYPE_MAP.get(battle_type_id)
    if not battle_type:
        # フォールバック: API の名前フィールドから推定
        name = (replay.get('replay_battle_type_name') or '').lower()
        if 'ranked' in name:
            battle_type = 'ranked'
        elif 'casual' in name:
            battle_type = 'casual'
        elif 'custom' in name:
            battle_type = 'custom'
        else:
            battle_type = 'other'

    # タイムスタンプ (Unix → ISO 8601 JST)
    uploaded_at = replay.get('uploaded_at', 0)
    if uploaded_at:
        played_at = datetime.fromtimestamp(uploaded_at, tz=c.JST).isoformat()
    else:
        played_at = c.get_now().isoformat()

    return {
        'replay_id': str(replay.get('replay_id', '')),
        'played_at': played_at,
        'battle_type': battle_type,
        'my_character': me.get('playing_character_name', ''),
        'opp_character': opp.get('playing_character_name', ''),
        'opp_name': opp.get('player', {}).get('fighter_id', ''),
        'result': result,
        'lp_before': None,  # API は現在値のみ提供、差分は不明
        'lp_after': me.get('league_point'),
        'mr_before': None,
        'mr_after': me.get('master_rating'),
        'opp_lp': opp.get('league_point'),
        'opp_mr': opp.get('master_rating'),
        'raw_data': replay,
    }


def _generate_mock_matches():
    # 0〜3件のフェイクデータを生成
    weights = [0.10, 0.60, 0.20, 0.10]  # 0件, 1件, 2件, 3件
    count = random.choices([0, 1, 2, 3], weights=weights)[0]

    matches = []
    now = c.get_now()

    for i in range(count):
        result = random.choice(['win', 'lose'])
        lp_base = random.randint(5000, 25000)
        lp_delta = random.randint(20, 100)
        mr_base = random.randint(1000, 2000)
        mr_delta = random.randint(10, 50)

        if result == 'win':
            lp_after = lp_base + lp_delta
            mr_after = mr_base + mr_delta
        else:
            lp_after = lp_base - lp_delta
            mr_after = mr_base - mr_delta

        played_at = now - timedelta(minutes=random.randint(1, 5), seconds=random.randint(0, 59))

        opp_mr_val = random.randint(1000, 2200)

        match = {
            'replay_id': f'MOCK-{uuid.uuid4().hex[:12]}',
            'played_at': played_at.isoformat(),
            'battle_type': random.choice(BATTLE_TYPES),
            'my_character': random.choice(CHARACTERS),
            'opp_character': random.choice(CHARACTERS),
            'opp_name': f'Player_{random.randint(1000, 9999)}',
            'result': result,
            'lp_before': lp_base,
            'lp_after': lp_after,
            'mr_before': mr_base,
            'mr_after': mr_after,
            'opp_lp': None,
            'opp_mr': opp_mr_val,
            'raw_data': None,
        }
        matches.append(match)

    return matches
