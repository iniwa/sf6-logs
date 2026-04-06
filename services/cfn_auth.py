import json
import requests
from bs4 import BeautifulSoup

import config as c
from services import storage

BUCKLER_BASE = 'https://www.streetfighter.com'
BUCKLER_TOP = f'{BUCKLER_BASE}/6/buckler'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

# BuildID キャッシュ
_build_id_cache = {'value': None}


def save_cookie(cookie_string):
    storage.set_config('cfn_cookie', cookie_string)
    # Cookie 変更時は BuildID キャッシュをクリア
    _build_id_cache['value'] = None
    c.log('CFN cookie saved')


def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ja,en;q=0.9',
    })
    cookie = storage.get_config('cfn_cookie')
    if cookie:
        session.headers.update({'Cookie': cookie})
    return session


def get_build_id(session=None, force_refresh=False):
    """メインページの #__NEXT_DATA__ から BuildID を取得"""
    if not force_refresh and _build_id_cache['value']:
        return _build_id_cache['value']

    if session is None:
        session = get_session()

    try:
        resp = session.get(BUCKLER_TOP, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        next_data = soup.find('script', id='__NEXT_DATA__')
        if not next_data:
            c.log('BuildID: __NEXT_DATA__ not found')
            return None

        data = json.loads(next_data.string)
        build_id = data.get('buildId')
        if build_id:
            _build_id_cache['value'] = build_id
            c.log(f'BuildID: {build_id}')
        return build_id

    except Exception as e:
        c.log(f'BuildID fetch error: {e}')
        return None


def is_authenticated():
    """Cookie の有効性を確認"""
    mock_mode = storage.get_config('mock_mode', 'true')
    if mock_mode == 'true':
        return True

    cookie = storage.get_config('cfn_cookie')
    if not cookie:
        return False

    # BuildID 取得で認証確認を兼ねる
    session = get_session()
    build_id = get_build_id(session)
    return build_id is not None


def clear_auth():
    storage.set_config('cfn_cookie', '')
    _build_id_cache['value'] = None
    c.log('CFN auth cleared')


def build_api_url(path, build_id=None):
    """_next/data API の URL を構築"""
    if build_id is None:
        build_id = get_build_id()
    if not build_id:
        return None
    return f'{BUCKLER_BASE}/6/buckler/_next/data/{build_id}/en/{path}'
