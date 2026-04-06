import json
import re
import base64
import requests
from bs4 import BeautifulSoup

import config as c
from services import storage

class TwoFactorRequired(Exception):
    """2FA が有効なアカウントで自動ログイン不可"""
    pass


BUCKLER_BASE = 'https://www.streetfighter.com'
BUCKLER_TOP = f'{BUCKLER_BASE}/6/buckler'
AUTH0_DOMAIN = 'auth.cid.capcom.com'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

# BuildID キャッシュ
_build_id_cache = {'value': None}


def save_cookie(cookie_string):
    storage.set_config('cfn_cookie', cookie_string)
    storage.set_config('cfn_cookie_saved_at', c.get_now().isoformat())
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
    storage.set_config('cfn_cookie_saved_at', '')
    _build_id_cache['value'] = None
    c.log('CFN auth cleared')


def build_api_url(path, build_id=None):
    """_next/data API の URL を構築"""
    if build_id is None:
        build_id = get_build_id()
    if not build_id:
        return None
    return f'{BUCKLER_BASE}/6/buckler/_next/data/{build_id}/en/{path}'


# --- Auto Login ---

def is_playwright_available():
    """Playwright がインストールされているか確認"""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def _requests_login(email, password):
    """requests ベースの自動ログイン (従来の実装)

    Returns:
        True: ログイン成功
    Raises:
        TwoFactorRequired: 2FA が有効な場合
        Exception: その他のログイン失敗
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja,en;q=0.9',
        'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'dnt': '1',
    })

    # Step 1: Auth config を取得
    c.log('Auto-login: fetching auth config...')
    resp = session.get(
        f'{BUCKLER_BASE}/6/buckler/auth/logineq',
        params={'redirect_url': '/?status=login'},
        timeout=15,
    )
    resp.raise_for_status()

    # atob('...') から Base64 エンコードされた設定を抽出
    match = re.search(r"atob\('([^']+)'\)", resp.text)
    if not match:
        raise Exception('Auth config not found in login page')

    auth_config = json.loads(base64.b64decode(match.group(1)).decode('utf-8'))
    client_id = auth_config.get('clientID')
    callback_url = auth_config.get('callbackURL')
    tenant = auth_config.get('auth0Tenant')
    extra = auth_config.get('extraParams', {})

    # Step 2: Auth0 にログイン
    c.log('Auto-login: authenticating with CAPCOM ID...')
    session.headers.update({
        'Content-Type': 'application/json',
        'Origin': f'https://{AUTH0_DOMAIN}',
        'Referer': f'https://{AUTH0_DOMAIN}/',
    })

    login_resp = session.post(
        f'https://{AUTH0_DOMAIN}/usernamepassword/login',
        json={
            'client_id': client_id,
            'redirect_uri': callback_url,
            'tenant': tenant,
            'response_type': extra.get('response_type', 'code'),
            'scope': extra.get('scope', 'openid profile email'),
            'state': extra.get('state', ''),
            '_csrf': extra.get('_csrf', ''),
            '_intstate': extra.get('_intstate', ''),
            'username': email,
            'password': password,
            'connection': 'Username-Password-Authentication',
            'sso': True,
            'protocol': extra.get('protocol', 'oauth2'),
        },
        timeout=15,
    )

    if login_resp.status_code == 401 or login_resp.status_code == 403:
        raise Exception('Login failed - invalid email or password')
    login_resp.raise_for_status()

    # 2FA/MFA 検出
    resp_text = login_resp.text
    if '"mfa_required"' in resp_text or '"multifactor"' in resp_text:
        raise TwoFactorRequired(
            '2FA/MFA is enabled on this CAPCOM ID. '
            'Automatic login is not supported with 2FA.'
        )

    # Step 3: コールバック実行（HTML フォームの hidden fields を送信）
    c.log('Auto-login: executing callback...')
    soup = BeautifulSoup(login_resp.text, 'html.parser')
    form = soup.find('form')
    if not form:
        raise Exception('Login failed - callback form not found (check credentials)')

    action_url = form.get('action')
    form_data = {}
    for inp in form.find_all('input', {'type': 'hidden'}):
        name = inp.get('name')
        if name:
            form_data[name] = inp.get('value', '')

    # Content-Type をフォーム送信に戻す
    session.headers.pop('Content-Type', None)
    session.headers.update({
        'Origin': BUCKLER_BASE,
        'Referer': f'https://{AUTH0_DOMAIN}/',
    })

    callback_resp = session.post(
        action_url,
        data=form_data,
        timeout=30,
        allow_redirects=True,
    )

    # Cookie を抽出（streetfighter.com ドメインのもの）
    buckler_cookies = []
    for cookie in session.cookies:
        if 'streetfighter.com' in (cookie.domain or ''):
            buckler_cookies.append(f'{cookie.name}={cookie.value}')

    if not buckler_cookies:
        raise Exception('Buckler cookies not found after login')

    cookie_string = '; '.join(buckler_cookies)
    save_cookie(cookie_string)

    c.log(f'Auto-login successful ({len(buckler_cookies)} cookies)')
    return True


def _playwright_login(email, password):
    """Playwright ベースのブラウザ自動ログイン (フォールバック)

    Returns:
        True: ログイン成功
    Raises:
        Exception: Playwright 未インストールまたはログイン失敗
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise Exception(
            'Playwright not installed. '
            'Install with: pip install playwright && playwright install chromium'
        )

    c.log('Playwright login: launching browser...')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        try:
            # Navigate to Buckler login
            page.goto(
                f'{BUCKLER_BASE}/6/buckler/auth/logineq?redirect_url=/?status=login',
                timeout=30000,
            )

            # Wait for Auth0 login form
            page.wait_for_selector(
                'input[name="email"], input[name="username"]',
                timeout=15000,
            )

            # Fill credentials
            email_input = (
                page.query_selector('input[name="email"]')
                or page.query_selector('input[name="username"]')
            )
            email_input.fill(email)
            page.fill('input[name="password"]', password)

            # Submit
            page.click('button[type="submit"]')

            # Wait for redirect back to Buckler
            page.wait_for_url('**/streetfighter.com/**', timeout=30000)

            # Extract cookies
            cookies = context.cookies()
            buckler_cookies = [
                f"{ck['name']}={ck['value']}"
                for ck in cookies
                if 'streetfighter.com' in ck.get('domain', '')
            ]

            if not buckler_cookies:
                raise Exception(
                    'Playwright: No Buckler cookies obtained after login'
                )

            cookie_string = '; '.join(buckler_cookies)
            save_cookie(cookie_string)
            c.log(f'Playwright login successful ({len(buckler_cookies)} cookies)')
            return True

        finally:
            browser.close()


def auto_login(email=None, password=None):
    """CAPCOM ID で自動ログインし、Cookie を取得・保存

    requests ベースのログインを試み、失敗時は Playwright フォールバックを使用。
    2FA 有効アカウントや認証情報エラーではフォールバックしない。

    Returns:
        True: ログイン成功
    Raises:
        TwoFactorRequired: 2FA が有効な場合
        Exception: ログイン失敗時
    """
    if not email:
        email = storage.get_config('capcom_email')
    if not password:
        password = storage.get_config('capcom_password')

    if not email or not password:
        raise Exception('CAPCOM ID credentials not configured')

    try:
        return _requests_login(email, password)
    except TwoFactorRequired:
        raise  # 2FA はフォールバックしない
    except Exception as e:
        if 'invalid email or password' in str(e).lower():
            raise  # 認証情報エラーはフォールバックしない
        c.log(f'Requests login failed: {e}, trying Playwright fallback...')
        return _playwright_login(email, password)


def refresh_cookie():
    """保存済み CAPCOM ID で Cookie を更新

    Returns:
        True: 更新成功, False: credentials 未設定, raises on error
    """
    email = storage.get_config('capcom_email')
    password = storage.get_config('capcom_password')
    if not email or not password:
        return False

    auto_login(email, password)
    return True
