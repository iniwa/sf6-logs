import threading
from apscheduler.schedulers.background import BackgroundScheduler

import config as c
from services import storage, cfn_auth, cfn_scraper

scheduler = BackgroundScheduler(timezone='Asia/Tokyo')

_status = {
    'last_fetch': None,
    'last_error': None,
    'error_count': 0,
    'matches_found': 0,
    'is_running': False,
}
_status_lock = threading.Lock()


def _poll_job():
    try:
        session = cfn_auth.get_session()
        matches = cfn_scraper.fetch_battle_log(session)

        new_count = 0
        for match in matches:
            if not storage.match_exists(match['replay_id']):
                storage.insert_match(match)
                new_count += 1

        with _status_lock:
            _status['last_fetch'] = c.get_now().isoformat()
            _status['last_error'] = None
            _status['matches_found'] += new_count

        if new_count > 0:
            c.log(f'Fetched {new_count} new match(es)')

    except Exception as e:
        with _status_lock:
            _status['last_error'] = str(e)
            _status['error_count'] += 1
        c.log(f'Poll error: {e}')


def start_scheduler():
    storage.init_db()
    interval = int(storage.get_config('poll_interval', '90'))
    scheduler.add_job(
        _poll_job, 'interval', seconds=interval,
        id='cfn_poll', replace_existing=True
    )
    scheduler.start()
    with _status_lock:
        _status['is_running'] = True
    c.log(f'Scheduler started (interval={interval}s)')


def stop_scheduler():
    scheduler.shutdown(wait=False)
    with _status_lock:
        _status['is_running'] = False
    c.log('Scheduler stopped')


def get_scheduler_status():
    with _status_lock:
        status = _status.copy()

    job = scheduler.get_job('cfn_poll')
    status['next_run'] = job.next_run_time.isoformat() if job and job.next_run_time else None
    return status
