import json
import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_column_if_missing(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _json_load(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                elo INTEGER DEFAULT 1000,
                role TEXT DEFAULT 'user',
                password TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        _add_column_if_missing(cursor, "users", "role", "TEXT DEFAULT 'user'")
        _add_column_if_missing(cursor, "users", "password", "TEXT")
        _add_column_if_missing(cursor, "users", "status", "TEXT DEFAULT 'active'")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                board TEXT,
                size INTEGER,
                turn TEXT,
                winner TEXT,
                winning_line TEXT,
                players TEXT,
                last_score TEXT,
                game_ended INTEGER DEFAULT 0,
                elo_already_updated INTEGER DEFAULT 0,
                last_move TEXT,
                move_history TEXT,
                turn_start_time REAL
            )
        """)
        # Migration for existing caro.db files.
        _add_column_if_missing(cursor, "rooms", "elo_already_updated", "INTEGER DEFAULT 0")
        _add_column_if_missing(cursor, "rooms", "last_move", "TEXT")
        _add_column_if_missing(cursor, "rooms", "move_history", "TEXT")
        _add_column_if_missing(cursor, "rooms", "turn_start_time", "REAL")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player TEXT,
                opponent TEXT,
                result TEXT,
                score TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing rows from older versions get safe defaults.
        cursor.execute("""
            UPDATE rooms
            SET move_history = '[]'
            WHERE move_history IS NULL OR move_history = ''
        """)
        conn.commit()
    finally:
        conn.close()


def update_user_role(username, new_role):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
        conn.commit()
    finally:
        conn.close()


def delete_user(username):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    finally:
        conn.close()


def update_user_status(username, status):
    conn = get_connection()
    try:
        _add_column_if_missing(conn.cursor(), "users", "status", "TEXT DEFAULT 'active'")
        conn.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
        conn.commit()
    finally:
        conn.close()


def get_user(username):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT username, elo, role, password, status FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        if not row:
            return None
        return {
            "username": row[0],
            "elo": int(row[1] or 1000),
            "role": row[2] or "user",
            "password": row[3],
            "status": row[4] or "active",
        }
    finally:
        conn.close()


def get_user_elo(username):
    user = get_user(username)
    return int(user["elo"]) if user else 1000


def get_user_role(username):
    user = get_user(username)
    return user["role"] if user else "user"


def create_user(username, elo=1000, role="user", password=None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, elo, role, password, status) VALUES (?, ?, ?, ?, 'active')",
            (username, elo, role, password),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def set_user_elo(username, elo):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET elo = ? WHERE username = ?", (int(elo), username))
        conn.commit()
    finally:
        conn.close()


def get_all_users():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT username, elo, role, status FROM users ORDER BY elo DESC, username ASC"
        ).fetchall()
        return [
            {
                "username": r[0],
                "elo": int(r[1] or 1000),
                "role": r[2] or "user",
                "status": r[3] or "active",
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_room(room_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT room_id, board, size, turn, winner, winning_line, players,
                   last_score, game_ended, elo_already_updated,
                   last_move, move_history, turn_start_time
            FROM rooms WHERE room_id = ?
            """,
            (room_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    last_move = _json_load(row[10], None)
    if isinstance(last_move, list) and len(last_move) == 2:
        last_move = (int(last_move[0]), int(last_move[1]))

    return {
        "room_id": row[0],
        "board": _json_load(row[1], []),
        "size": int(row[2] or 3),
        "turn": row[3] or "X",
        "winner": row[4],
        "winning_line": _json_load(row[5], []),
        "players": _json_load(row[6], {}),
        "last_score": _json_load(row[7], None),
        "game_ended": bool(row[8]),
        "elo_already_updated": bool(row[9]),
        "last_move": last_move,
        "move_history": _json_load(row[11], []),
        "turn_start_time": row[12],
    }


def get_room_info(room_id):
    return get_room(room_id)


def save_room(room_id, room_data):
    """Insert/update a room without dropping its persistent history."""
    board = room_data.get("board", [])
    size = int(room_data.get("size", len(board) or 3))
    turn = room_data.get("turn", "X")
    winner = room_data.get("winner")
    winning_line = room_data.get("winning_line", []) or []
    players = room_data.get("players", {}) or {}
    last_score = room_data.get("last_score")
    game_ended = 1 if room_data.get("game_ended", False) else 0
    elo_updated = 1 if room_data.get("elo_already_updated", False) else 0
    last_move = room_data.get("last_move")
    move_history = room_data.get("move_history", []) or []
    turn_start_time = room_data.get("turn_start_time")

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO rooms (
                room_id, board, size, turn, winner, winning_line, players,
                last_score, game_ended, elo_already_updated,
                last_move, move_history, turn_start_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                board = excluded.board,
                size = excluded.size,
                turn = excluded.turn,
                winner = excluded.winner,
                winning_line = excluded.winning_line,
                players = excluded.players,
                last_score = excluded.last_score,
                game_ended = excluded.game_ended,
                elo_already_updated = excluded.elo_already_updated,
                last_move = excluded.last_move,
                move_history = excluded.move_history,
                turn_start_time = excluded.turn_start_time
        """, (
            room_id,
            json.dumps(board, ensure_ascii=False),
            size,
            turn,
            winner,
            json.dumps(winning_line, ensure_ascii=False),
            json.dumps(players, ensure_ascii=False),
            json.dumps(last_score, ensure_ascii=False) if last_score is not None else None,
            game_ended,
            elo_updated,
            json.dumps(last_move, ensure_ascii=False) if last_move is not None else None,
            json.dumps(move_history, ensure_ascii=False),
            turn_start_time,
        ))
        conn.commit()
    finally:
        conn.close()


def delete_room(room_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
        conn.commit()
    finally:
        conn.close()


def add_match_history(player, opponent, result, score):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO match_history (player, opponent, result, score) VALUES (?, ?, ?, ?)",
            (player, opponent, result, score),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_matches(limit=10):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT player, opponent, result, score, timestamp
            FROM match_history
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {"player": r[0], "opponent": r[1], "result": r[2], "score": r[3], "timestamp": r[4]}
            for r in rows
        ]
    finally:
        conn.close()
