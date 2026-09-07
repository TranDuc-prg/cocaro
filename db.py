# db.py (Đã tích hợp hoàn chỉnh quản lý cột status)
import sqlite3
import json
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            elo INTEGER DEFAULT 1000,
            role TEXT DEFAULT 'user',
            password TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'role' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if 'password' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password TEXT")
    if 'status' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")

    cursor.execute('''
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
            elo_already_updated INTEGER DEFAULT 0
        )
    ''')
    cursor.execute("PRAGMA table_info(rooms)")
    room_columns = [col[1] for col in cursor.fetchall()]
    if 'elo_already_updated' not in room_columns:
        cursor.execute("ALTER TABLE rooms ADD COLUMN elo_already_updated INTEGER DEFAULT 0")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT,
            opponent TEXT,
            result TEXT,
            score TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def update_user_role(username, new_role):
    """Cập nhật quyền hạn (role) cho người dùng"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
    conn.commit()
    conn.close()

def delete_user(username):
    """Xóa tài khoản người dùng khỏi hệ thống"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def update_user_status(username, status):
    """Cập nhật trạng thái tài khoản ('active' hoặc 'locked')"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
        cursor.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
    conn.commit()
    conn.close()

def get_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kiểm tra xem bảng đã có cột status chưa để tránh lỗi truy vấn
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'status' in columns:
        cursor.execute("SELECT username, elo, role, password, status FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'username': row[0], 'elo': row[1], 'role': row[2], 'password': row[3], 'status': row[4] or 'active'}
    else:
        cursor.execute("SELECT username, elo, role, password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'username': row[0], 'elo': row[1], 'role': row[2], 'password': row[3], 'status': 'active'}
    return None

def get_user_elo(username):
    user = get_user(username)
    return user['elo'] if user else 1000

def get_user_role(username):
    user = get_user(username)
    return user['role'] if user else 'user'

def create_user(username, elo=1000, role='user', password=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, elo, role, password, status) VALUES (?, ?, ?, ?, 'active')",
                       (username, elo, role, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def set_user_elo(username, elo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET elo = ? WHERE username = ?", (elo, username))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'status' in columns:
        cursor.execute("SELECT username, elo, role, status FROM users ORDER BY elo DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{'username': r[0], 'elo': r[1], 'role': r[2], 'status': r[3] or 'active'} for r in rows]
    else:
        cursor.execute("SELECT username, elo, role FROM users ORDER BY elo DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{'username': r[0], 'elo': r[1], 'role': r[2], 'status': 'active'} for r in rows]

def get_room(room_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'room_id': row[0],
            'board': json.loads(row[1]),
            'size': row[2],
            'turn': row[3],
            'winner': row[4],
            'winning_line': json.loads(row[5]) if row[5] else [],
            'players': json.loads(row[6]) if row[6] else {},
            'last_score': json.loads(row[7]) if row[7] else None,
            'game_ended': bool(row[8]),
            'elo_already_updated': bool(row[9]) if len(row) > 9 and row[9] is not None else False
        }
    return None

def save_room(room_id, room_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO rooms (room_id, board, size, turn, winner, winning_line, players, last_score, game_ended, elo_already_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        room_id,
        json.dumps(room_data['board']),
        room_data['size'],
        room_data['turn'],
        room_data['winner'],
        json.dumps(room_data['winning_line']),
        json.dumps(room_data['players']),
        json.dumps(room_data['last_score']) if room_data['last_score'] is not None else None,
        1 if room_data['game_ended'] else 0,
        1 if room_data.get('elo_already_updated') else 0
    ))
    conn.commit()
    conn.close()

def delete_room(room_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()

def add_match_history(player, opponent, result, score):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO match_history (player, opponent, result, score)
        VALUES (?, ?, ?, ?)
    ''', (player, opponent, result, score))
    conn.commit()
    conn.close()

def get_recent_matches(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT player, opponent, result, score, timestamp
        FROM match_history
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{'player': r[0], 'opponent': r[1], 'result': r[2], 'score': r[3], 'timestamp': r[4]} for r in rows]