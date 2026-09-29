"""Consecutive background-operation failures, independent of retained history."""
import threading

import config as c

THRESHOLD = 3
_counts = {}
_lock = threading.Lock()


def success(operation):
    with _lock:
        _counts.pop(operation, None)


def failure(operation, message, *, exc_info=True, count=None):
    with _lock:
        if count is None:
            count = _counts.get(operation, 0) + 1
            _counts[operation] = count
    if count >= THRESHOLD:
        c.log(f'{message} (consecutive failures: {count})', exc_info=exc_info)
    else:
        c.log(f'{operation}: waiting for retry ({count}/{THRESHOLD})')
