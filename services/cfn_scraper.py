import random
import uuid
from datetime import timedelta

import config as c
from services import storage

# SF6 キャラクターリスト
CHARACTERS = [
    'Ryu', 'Ken', 'Chun-Li', 'Luke', 'Jamie', 'Kimberly',
    'Juri', 'Guile', 'JP', 'Dhalsim', 'Cammy', 'Manon',
    'Dee Jay', 'Lily', 'Zangief', 'Marisa', 'Blanka', 'Honda',
    'Rashid', 'A.K.I.', 'Ed', 'Akuma', 'M. Bison', 'Terry',
    'Mai', 'Elena', 'Gouki',
]

BATTLE_TYPES = ['ranked', 'casual']


def fetch_battle_log(session=None):
    mock_mode = storage.get_config('mock_mode', 'true')
    if mock_mode == 'true':
        return _generate_mock_matches()

    return _fetch_real_battle_log(session)


def _fetch_real_battle_log(session):
    # TODO: 実際のCFNスクレイピング実装
    c.log('Real CFN scraping not implemented yet')
    return []


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
            'raw_data': None,
        }
        matches.append(match)

    return matches
