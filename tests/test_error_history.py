import threading

import pytest

from services import error_history


@pytest.fixture(autouse=True)
def clean_history():
    error_history.clear()
    yield
    error_history.clear()


def test_history_is_newest_first_bounded_and_safe():
    class SecretError(Exception):
        pass

    for index in range(error_history.MAX_RECENT_ERRORS + 3):
        error_history.record('poll', SecretError('cookie=secret https://private/body'), kind='network')
    events = error_history.get_recent_errors()
    assert len(events) == error_history.MAX_RECENT_ERRORS
    assert events[0]['source'] == 'poll'
    assert events[0]['kind'] == 'network'
    assert events[0]['exception_type'] == 'SecretError'
    assert all('secret' not in repr(event) for event in events)


def test_history_snapshot_is_copied_and_http_response_falsey_is_supported():
    class Response:
        status_code = 503
        def __bool__(self):
            return False

    error = RuntimeError('Authorization: secret')
    error.response = Response()
    error_history.record('poll', error)
    snapshot = error_history.get_recent_errors()
    snapshot[0]['summary'] = 'changed'
    assert error_history.get_recent_errors()[0]['summary'] == 'サービス利用不可'
    assert error_history.get_recent_errors()[0]['status_code'] == 503


def test_history_concurrent_recording_and_snapshotting():
    def write():
        for _ in range(100):
            error_history.record('replay_parse', ValueError('secret'), kind='parse')

    threads = [threading.Thread(target=write) for _ in range(4)]
    for thread in threads:
        thread.start()
    snapshots = []
    for _ in range(100):
        snapshots.append(error_history.get_recent_errors())
    for thread in threads:
        thread.join()
    assert len(error_history.get_recent_errors()) == error_history.MAX_RECENT_ERRORS
    assert all(len(snapshot) <= error_history.MAX_RECENT_ERRORS for snapshot in snapshots)
