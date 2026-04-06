import os
import sqlite3
import json
import config as c


_post_insert_hooks = []


def register_post_insert_hook(fn):
    _post_insert_hooks.append(fn)


def _connect():
    os.makedirs(os.path.dirname(c.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(c.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with c.db_lock:
        conn = _connect()
        try:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS matches (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    replay_id    TEXT UNIQUE NOT NULL,
                    played_at    DATETIME NOT NULL,
                    battle_type  TEXT NOT NULL,
                    my_character TEXT NOT NULL,
                    opp_character TEXT NOT NULL,
                    opp_name     TEXT NOT NULL,
                    result       TEXT NOT NULL,
                    lp_before    INTEGER,
                    lp_after     INTEGER,
                    mr_before    INTEGER,
                    mr_after     INTEGER,
                    raw_data     TEXT,
                    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at DATETIME NOT NULL,
                    ended_at   DATETIME,
                    label      TEXT
                );

                CREATE TABLE IF NOT EXISTS config (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            ''')
            conn.commit()
            c.log('DB initialized')
        finally:
            conn.close()


# --- Config ---

def get_config(key, default=None):
    with c.db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                'SELECT value FROM config WHERE key = ?', (key,)
            ).fetchone()
            return row['value'] if row else (default or c.DEFAULT_CONFIG.get(key, ''))
        finally:
            conn.close()


def set_config(key, value):
    with c.db_lock:
        conn = _connect()
        try:
            conn.execute(
                'INSERT INTO config (key, value) VALUES (?, ?) '
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                (key, str(value))
            )
            conn.commit()
        finally:
            conn.close()


def load_all_config():
    conf = c.DEFAULT_CONFIG.copy()
    with c.db_lock:
        conn = _connect()
        try:
            rows = conn.execute('SELECT key, value FROM config').fetchall()
            for row in rows:
                conf[row['key']] = row['value']
        finally:
            conn.close()
    return conf


# --- Matches ---

def match_exists(replay_id):
    with c.db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                'SELECT 1 FROM matches WHERE replay_id = ?', (replay_id,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()


def insert_match(match_dict):
    with c.db_lock:
        conn = _connect()
        try:
            conn.execute(
                '''INSERT OR IGNORE INTO matches
                   (replay_id, played_at, battle_type, my_character,
                    opp_character, opp_name, result,
                    lp_before, lp_after, mr_before, mr_after, raw_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    match_dict['replay_id'],
                    match_dict['played_at'],
                    match_dict['battle_type'],
                    match_dict['my_character'],
                    match_dict['opp_character'],
                    match_dict['opp_name'],
                    match_dict['result'],
                    match_dict.get('lp_before'),
                    match_dict.get('lp_after'),
                    match_dict.get('mr_before'),
                    match_dict.get('mr_after'),
                    json.dumps(match_dict.get('raw_data'), ensure_ascii=False)
                    if match_dict.get('raw_data') else None,
                )
            )
            conn.commit()
            inserted = conn.total_changes > 0
            if inserted:
                for hook in _post_insert_hooks:
                    try:
                        hook(match_dict)
                    except Exception:
                        pass
            return inserted
        finally:
            conn.close()


def get_matches(limit=50, offset=0, battle_type=None):
    with c.db_lock:
        conn = _connect()
        try:
            sql = 'SELECT * FROM matches'
            params = []
            if battle_type:
                sql += ' WHERE battle_type = ?'
                params.append(battle_type)
            sql += ' ORDER BY played_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


def get_matches_since(since_dt):
    with c.db_lock:
        conn = _connect()
        try:
            rows = conn.execute(
                'SELECT * FROM matches WHERE played_at >= ? ORDER BY played_at DESC',
                (since_dt.isoformat(),)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


# --- Sessions ---

def start_session(label=None):
    with c.db_lock:
        conn = _connect()
        try:
            cur = conn.execute(
                'INSERT INTO sessions (started_at, label) VALUES (?, ?)',
                (c.get_now().isoformat(), label)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def end_session(session_id=None):
    with c.db_lock:
        conn = _connect()
        try:
            if session_id:
                conn.execute(
                    'UPDATE sessions SET ended_at = ? WHERE id = ?',
                    (c.get_now().isoformat(), session_id)
                )
            else:
                conn.execute(
                    'UPDATE sessions SET ended_at = ? WHERE ended_at IS NULL',
                    (c.get_now().isoformat(),)
                )
            conn.commit()
        finally:
            conn.close()


def get_current_session():
    with c.db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                'SELECT * FROM sessions WHERE ended_at IS NULL '
                'ORDER BY started_at DESC LIMIT 1'
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
