import requests
import config as c
from services import storage


def save_cookie(cookie_string):
    storage.set_config('cfn_cookie', cookie_string)
    c.log('CFN cookie saved')


def get_session():
    session = requests.Session()
    cookie = storage.get_config('cfn_cookie')
    if cookie:
        session.headers.update({'Cookie': cookie})
    return session


def is_authenticated():
    mock_mode = storage.get_config('mock_mode', 'true')
    if mock_mode == 'true':
        return True
    cookie = storage.get_config('cfn_cookie')
    return bool(cookie)


def clear_auth():
    storage.set_config('cfn_cookie', '')
    c.log('CFN auth cleared')
