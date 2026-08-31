"""Safe, bounded history of recent CFN failures."""

import re
import threading
from collections import deque

import requests

import config as c

MAX_RECENT_ERRORS = 20
_errors = deque(maxlen=MAX_RECENT_ERRORS)
_lock = threading.Lock()
_SOURCES = {
    'poll': '戦績取得', 'auto_login': '自動ログイン',
    'auth_check': '認証確認', 'build_id': 'BuildID取得',
    'auto_login_requests': '自動ログイン(requests)',
    'replay_parse': '戦績解析', 'login_test': 'ログインテスト',
}
_KINDS = {'auth', 'network', 'rate_limit', 'response', 'configuration',
          'unavailable', 'parse', 'two_factor', 'unexpected'}
_SUMMARY = {
    'auth': '認証エラー', 'network': 'ネットワークエラー',
    'rate_limit': 'リクエスト制限', 'response': '応答エラー',
    'configuration': '設定エラー', 'unavailable': 'サービス利用不可',
    'parse': '応答解析エラー', 'two_factor': '2FAが必要',
    'unexpected': '予期しないエラー',
}
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_.-]{0,63}$')


def _safe_attribute(value, name):
    """Diagnostic metadata must not interrupt the original failure handler."""
    try:
        return getattr(value, name, None)
    except Exception:
        return None


def _exception_type(error):
    if error is None:
        return None
    name = _safe_attribute(type(error), '__name__')
    return name if isinstance(name, str) and _IDENTIFIER.fullmatch(name) else 'Exception'


def _validated_status_code(value):
    return value if type(value) is int and 100 <= value <= 599 else None


def _status_code(error):
    value = _safe_attribute(error, 'status_code')
    if value is None:
        response = _safe_attribute(error, 'response')
        # requests.Response is falsey for 4xx/5xx; do not use ``if response``.
        value = _safe_attribute(response, 'status_code')
    return _validated_status_code(value)


def record(source, error=None, *, kind=None, status_code=None):
    """Retain safe metadata only, never the exception or its message/content."""
    source = source if isinstance(source, str) and source in _SOURCES else 'unexpected'
    status_code = (
        _status_code(error) if status_code is None
        else _validated_status_code(status_code)
    )
    kind = next((
        value for value in (kind, _safe_attribute(error, 'kind'))
        if isinstance(value, str) and value in _KINDS
    ), None)
    if kind is None:
        if status_code in (401, 403):
            kind = 'auth'
        elif status_code == 429:
            kind = 'rate_limit'
        elif status_code is not None and 400 <= status_code <= 499:
            kind = 'response'
        elif status_code is not None and 500 <= status_code <= 599:
            kind = 'unavailable'
        elif isinstance(error, requests.RequestException):
            kind = 'network'
    kind = kind if kind in _KINDS else 'unexpected'
    event = {
        'source': source,
        'source_label': _SOURCES.get(source, 'その他'),
        'kind': kind,
        'summary': _SUMMARY[kind],
        'exception_type': _exception_type(error),
        'status_code': status_code,
    }
    with _lock:
        # Timestamp and insertion share an order across scheduler/web threads.
        event['timestamp'] = c.get_now().isoformat()
        _errors.appendleft(event)
    return event.copy()


def get_recent_errors():
    with _lock:
        return [event.copy() for event in _errors]


def clear():
    with _lock:
        _errors.clear()
