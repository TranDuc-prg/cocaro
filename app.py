import io
import time
import copy
import json
import random
import sqlite3
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_image_coordinates import streamlit_image_coordinates

from helpers import generate_room_id
from config import DB_PATH
from db import (
    get_user_elo, set_user_elo, get_all_users, get_recent_matches,
    init_db, get_room, save_room, add_match_history
)
from room_manager import init_room, join_room, leave_room, get_room_info
from game_logic import check_winner, is_full, ai_move, apply_move, get_ai_hint, minimax, benchmark_algorithms
from elo import update_elo_online

from dangnhap import render_login_page
from dangky import render_register_page
from admin import render_admin_page

def get_level(elo):
    return max(1, elo // 100)

@st.cache_data(ttl=60)
def cached_get_all_users():
    return get_all_users()

@st.cache_data(ttl=60)
def cached_get_recent_matches(limit=10):
    return get_recent_matches(limit)

init_db()

def init_feedback_table():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                room_id TEXT,
                result TEXT,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TEXT NOT NULL,
                game_token TEXT,
                admin_reply TEXT,
                status TEXT DEFAULT 'new',
                replied_at TEXT
            )
        """)

        cursor.execute("PRAGMA table_info(game_feedback)")
        columns = [row[1] for row in cursor.fetchall()]
        if "game_token" not in columns:
            cursor.execute("ALTER TABLE game_feedback ADD COLUMN game_token TEXT")
        if "admin_reply" not in columns:
            cursor.execute("ALTER TABLE game_feedback ADD COLUMN admin_reply TEXT")
        if "status" not in columns:
            cursor.execute("ALTER TABLE game_feedback ADD COLUMN status TEXT DEFAULT 'new'")
        if "replied_at" not in columns:
            cursor.execute("ALTER TABLE game_feedback ADD COLUMN replied_at TEXT")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Không thể khởi tạo/nâng cấp bảng game_feedback: {e}")


def save_game_feedback(username, game_mode, room_id, result, rating, comment, game_token):
    """Lưu đánh giá của người chơi vào SQLite, gắn với đúng ván đấu."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO game_feedback
        (username, game_mode, room_id, result, rating, comment, created_at, game_token)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        username,
        game_mode,
        room_id,
        result,
        int(rating),
        (comment or "").strip(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        game_token
    ))
    conn.commit()
    conn.close()


def get_feedback_for_game(username, game_mode, room_id, game_token):
    """Lấy đánh giá của user cho đúng ván hiện tại."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, game_mode, room_id, result, rating, comment, created_at, game_token,
                   admin_reply, status, replied_at
            FROM game_feedback
            WHERE username = ? AND game_mode = ? AND COALESCE(room_id, '') = COALESCE(?, '')
              AND game_token = ?
            ORDER BY id DESC
            LIMIT 1
        """, (username, game_mode, room_id, game_token))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"Không thể đọc đánh giá hiện tại: {e}")
        return None


def get_user_feedback_history(username, limit=10):
    """Lấy lịch sử đánh giá gần nhất của user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_mode, room_id, result, rating, comment, created_at,
                   admin_reply, status, replied_at
            FROM game_feedback
            WHERE username = ?
            ORDER BY id DESC
            LIMIT ?
        """, (username, int(limit)))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Không thể đọc lịch sử đánh giá: {e}")
        return []


def has_submitted_feedback(username, game_mode, room_id, result, game_token):
    """Kiểm tra đánh giá đã được lưu cho đúng user và đúng ván."""
    if not username or not game_token:
        return False
    return get_feedback_for_game(username, game_mode, room_id, game_token) is not None


def get_player_matches(username, limit=20):
    """Lấy lịch sử trận đấu của riêng người chơi hiện tại."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT player, opponent, result, score, timestamp
            FROM match_history
            WHERE player = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (username, int(limit))
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Không thể đọc lịch sử người chơi: {e}")
        return []


def get_player_stats(username):
    """Thống kê thắng/thua/hòa từ match_history."""
    matches = get_player_matches(username, 10000)
    wins = losses = draws = 0
    for item in matches:
        result = str(item.get("result") or "").strip().lower()
        if result.startswith("thắng"):
            wins += 1
        elif result.startswith("thua"):
            losses += 1
        elif result.startswith("hòa") or result.startswith("hoa"):
            draws += 1
    total = wins + losses + draws
    win_rate = round((wins / total) * 100, 1) if total else 0.0
    return {"total": total, "wins": wins, "losses": losses, "draws": draws, "win_rate": win_rate}


def get_feedback_summary(username):
    """Tổng hợp đánh giá của người chơi hiện tại."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(ROUND(AVG(rating), 1), 0) AS avg_rating,
                SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) AS five_star,
                SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS low_rating
            FROM game_feedback
            WHERE username = ?
            """,
            (username,)
        ).fetchone()
        recent = conn.execute(
            """
            SELECT game_mode, result, rating, comment, created_at, status, admin_reply
            FROM game_feedback
            WHERE username = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (username,)
        ).fetchall()
        conn.close()
        return {
            "total": int(row["total"] or 0),
            "avg_rating": float(row["avg_rating"] or 0),
            "five_star": int(row["five_star"] or 0),
            "low_rating": int(row["low_rating"] or 0),
            "recent": [dict(item) for item in recent]
        }
    except Exception as e:
        print(f"Không thể đọc tổng hợp đánh giá: {e}")
        return {"total": 0, "avg_rating": 0.0, "five_star": 0, "low_rating": 0, "recent": []}


def build_replay_board(size, moves, step):
    """Dựng lại bàn cờ sau N nước đi từ move_history."""
    board = [[" " for _ in range(size)] for _ in range(size)]
    safe_step = max(0, min(int(step), len(moves)))
    last_move = None
    for move in moves[:safe_step]:
        try:
            row = int(move.get("row", 1)) - 1
            col = int(move.get("col", 1)) - 1
            symbol = move.get("symbol", " " )
            if 0 <= row < size and 0 <= col < size and symbol in ("X", "O"):
                board[row][col] = symbol
                last_move = (row, col)
        except (TypeError, ValueError):
            continue
    return board, last_move


def render_move_replay(moves, size, key_prefix="replay_online", title="▶️ Replay từng nước đi"):
    """Replay tương tác: chọn bước, quay lại và đi tới từng nước."""
    if not moves:
        st.info("Chưa có dữ liệu replay.")
        return

    signature = f"{len(moves)}|{moves[-1].get('timestamp', moves[-1].get('row', ''))}"
    signature_key = f"{key_prefix}_signature"
    step_key = f"{key_prefix}_step"
    if st.session_state.get(signature_key) != signature:
        st.session_state[signature_key] = signature
        st.session_state[step_key] = 0

    st.markdown(f"### {title}")
    max_step = len(moves)
    current_step = int(st.session_state.get(step_key, 0))

    # Slider phải được cập nhật trước khi widget được tạo.
    current_step = max(0, min(current_step, max_step))
    st.session_state[step_key] = current_step
    selected_step = st.slider(
        "Chọn nước đi",
        min_value=0,
        max_value=max_step,
        value=current_step,
        key=f"{key_prefix}_slider",
        format="Nước %d"
    )
    st.session_state[step_key] = selected_step

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⏮ Trước", key=f"{key_prefix}_prev", use_container_width=True, disabled=selected_step <= 0):
            st.session_state[step_key] = max(0, selected_step - 1)
            st.rerun()
    with c2:
        if st.button("🔄 Về đầu", key=f"{key_prefix}_reset", use_container_width=True, disabled=selected_step == 0):
            st.session_state[step_key] = 0
            st.rerun()
    with c3:
        if st.button("⏭ Tiếp", key=f"{key_prefix}_next", use_container_width=True, disabled=selected_step >= max_step):
            st.session_state[step_key] = min(max_step, selected_step + 1)
            st.rerun()

    replay_board, replay_last = build_replay_board(size, moves, selected_step)
    replay_img = draw_caro_board(replay_board, size, winning_line=[], last_move=replay_last)
    rc1, rc2, rc3 = st.columns([1, 2, 1])
    with rc2:
        st.image(replay_img, width=420)

    if selected_step > 0:
        move = moves[selected_step - 1]
        st.info(
            f"**Nước {selected_step}/{max_step}:** {move.get('symbol', '?')} - {move.get('player', 'N/A')} | "
            f"Hàng {move.get('row', '?')}, Cột {move.get('col', '?')}"
        )
    else:
        st.caption("Đang ở trạng thái bàn cờ ban đầu.")


init_feedback_table()

st.set_page_config(
    page_title="Cờ Caro Trực Tuyến - EAUT",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Session State Initialization ----
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "size" not in st.session_state:
    st.session_state.size = 3
if "board" not in st.session_state:
    st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
if "turn" not in st.session_state:
    st.session_state.turn = "X"
if "winner" not in st.session_state:
    st.session_state.winner = None
if "winning_line" not in st.session_state:
    st.session_state.winning_line = []
if "game_mode" not in st.session_state:
    st.session_state.game_mode = "vs_ai"
if "room_id" not in st.session_state:
    st.session_state.room_id = "phong_mac_dinh"
if "is_room_creator" not in st.session_state:
    st.session_state.is_room_creator = False
if "my_symbol" not in st.session_state:
    st.session_state.my_symbol = "X"
if "win_score" not in st.session_state:
    st.session_state.win_score = None
if "show_winner_overlay" not in st.session_state:
    st.session_state.show_winner_overlay = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"
if "elo_updated_online" not in st.session_state:
    st.session_state.elo_updated_online = False
if "ai_stats" not in st.session_state:
    st.session_state.ai_stats = None
if "ai_metrics_history" not in st.session_state:
    st.session_state.ai_metrics_history = []
if "ai_vs_ai_history" not in st.session_state:
    st.session_state.ai_vs_ai_history = []
if "ai_vs_ai_boards" not in st.session_state:
    st.session_state.ai_vs_ai_boards = []
# Lưu kết quả benchmark để không bị mất sau st_autorefresh mỗi 1 giây
if "benchmark_result" not in st.session_state:
    st.session_state.benchmark_result = None
if "benchmark_depth_used" not in st.session_state:
    st.session_state.benchmark_depth_used = None
if "benchmark_size_used" not in st.session_state:
    st.session_state.benchmark_size_used = None
if "hint_move" not in st.session_state:
    st.session_state.hint_move = None
if "board_history" not in st.session_state:
    st.session_state.board_history = []
if "ai_difficulty" not in st.session_state:
    st.session_state.ai_difficulty = "Trung bình"
if "last_move" not in st.session_state:
    st.session_state.last_move = None
if "ai_vs_ai_running" not in st.session_state:
    st.session_state.ai_vs_ai_running = False
if "overlay_celebrated" not in st.session_state:
    st.session_state.overlay_celebrated = False
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False
if "feedback_game_token" not in st.session_state:
    st.session_state.feedback_game_token = None
if "replay_online_step" not in st.session_state:
    st.session_state.replay_online_step = 0
if "replay_online_signature" not in st.session_state:
    st.session_state.replay_online_signature = None
if "online_turn_time_limit" not in st.session_state:
    st.session_state.online_turn_time_limit = 0

# ---- Pause Game State Initialization ----
if "game_paused" not in st.session_state:
    st.session_state.game_paused = False
if "paused_elapsed_time" not in st.session_state:
    st.session_state.paused_elapsed_time = 0
if "extra_paused_duration" not in st.session_state:
    st.session_state.extra_paused_duration = 0

# ---- Turn Timer State Initialization ----
if "turn_time_limit" not in st.session_state:
    st.session_state.turn_time_limit = 30
if "turn_start_time" not in st.session_state:
    st.session_state.turn_start_time = time.time()

# Tự động làm mới giao diện mỗi 1 giây để cập nhật đồng hồ và nhận nước đi mới
st_autorefresh(interval=1000, key="caro_global_refresh")

if st.session_state.get('trigger_rerun'):
    st.session_state['trigger_rerun'] = False
    st.rerun()

if st.query_params.get("reset") == "true":
    if st.session_state.get("game_mode", "vs_ai") in ["vs_ai", "ai_vs_ai", "benchmark"]:
        size = st.session_state.get("size", 3)
        st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
        st.session_state.turn = "X"
        st.session_state.winner = None
        st.session_state.winning_line = []
        st.session_state.win_score = None
        st.session_state.show_winner_overlay = False
        st.session_state.overlay_celebrated = False
        st.session_state.ai_stats = None
        st.session_state.ai_metrics_history = []
        st.session_state.ai_vs_ai_history = []
        st.session_state.ai_vs_ai_boards = []
        st.session_state.hint_move = None
        st.session_state.board_history = []
        st.session_state.last_move = None
        st.session_state.ai_vs_ai_running = False
        st.session_state.game_paused = False
        st.session_state.paused_elapsed_time = 0
        st.session_state.extra_paused_duration = 0
        st.session_state.turn_start_time = time.time()
        st.session_state.feedback_submitted = False
        st.session_state.feedback_game_token = None
    else:
        room_id = st.session_state.get("room_id", "phong_mac_dinh")
        room = get_room_info(room_id)
        if room:
            size = room["size"]
            room["board"] = [[" " for _ in range(size)] for _ in range(size)]
            room["turn"] = "X"
            room["winner"] = None
            room["winning_line"] = []
            room["last_score"] = None
            room["game_ended"] = False
            room["elo_already_updated"] = False
            room["last_move"] = None
            room["move_history"] = []
            room["turn_start_time"] = time.time()
            save_room(room_id, room)
            st.session_state.win_score = None
            st.session_state.show_winner_overlay = False
            st.session_state.overlay_celebrated = False
            st.session_state.elo_updated_online = False
    st.query_params.clear()
    st.session_state.replay_online_step = 0
    st.session_state.replay_online_signature = None
    st.session_state['trigger_rerun'] = True

if st.session_state.board == [] and st.session_state.game_mode == "vs_ai":
    size = st.session_state.size
    st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]

current_size = st.session_state.size

def draw_caro_board(board, size, winning_line=[], last_move=None):
    img_size = 550  
    padding = 25
    board_draw_size = img_size - (2 * padding)
    cell_size = board_draw_size / size
    
    image = Image.new("RGB", (img_size, img_size), "#f3e5ab")
    draw = ImageDraw.Draw(image)
    
    draw.rectangle(
        [padding - 3, padding - 3, img_size - padding + 3, img_size - padding + 3],
        outline="#5c2c16", width=4
    )
    
    for r in range(size):
        for c in range(size):
            x1 = padding + (c * cell_size)
            y1 = padding + (r * cell_size)
            x2 = padding + ((c + 1) * cell_size)
            y2 = padding + ((r + 1) * cell_size)
            
            if (r, c) in winning_line:
                cell_color = "#4ade80"
            elif last_move and (r, c) == last_move:
                cell_color = "#f6ad55"
            else:
                cell_color = "#faedcd" if (r + c) % 2 == 0 else "#e9d8a6"
                
            draw.rectangle([x1, y1, x2, y2], fill=cell_color, outline="#bc6c25", width=1)
            
            val = board[r][c] if r < len(board) and c < len(board[r]) else " "
            if val != " ":
                try:
                    font_size_px = int(cell_size * 0.65)
                    font = ImageFont.truetype("arial.ttf", font_size_px)
                except:
                    font = ImageFont.load_default()
                
                color = "#e63946" if val == "X" else "#1d3557"
                
                bbox = draw.textbbox((0, 0), val, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                text_x = x1 + (cell_size - w) / 2 - bbox[0]
                text_y = y1 + (cell_size - h) / 2 - bbox[1]
                
                draw.text((text_x, text_y), val, fill=color, font=font)
                
    return image

css_code = """
<style>
    .stApp { background: #f8f9fa; }
    .main-title { text-align: center; color: #2c3e50; font-size: 32px; font-weight: 800; margin-bottom: 10px; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.2s ease-in-out; }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

if not st.session_state.current_user:
    _, col_switch, _ = st.columns([1, 1.2, 1])
    with col_switch:
        auth_choice = st.radio("", ["Đăng nhập", "Đăng ký"], horizontal=True, label_visibility="collapsed")
    
    if auth_choice == "Đăng nhập":
        render_login_page()
    else:
        render_register_page()
    st.stop()

user = st.session_state.current_user
user_score = get_user_elo(user)
user_role = st.session_state.user_role
current_level = get_level(user_score)

if st.query_params.get("room"):
    st.session_state.room_id = st.query_params["room"]
    if st.session_state.game_mode == "online_pvp":
        sym = join_room(st.session_state.room_id, user)
        if sym:
            st.session_state.my_symbol = sym

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown(f"### 👤 {user}")
    st.caption(f"Cấp độ: **Level {current_level}** | Elo: **{user_score}**")
    
    if st.button("🚪 Đăng xuất / Đổi tài khoản", use_container_width=True):
        if st.session_state.game_mode == "online_pvp" and st.session_state.room_id:
            leave_room(st.session_state.room_id, user)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.query_params.clear()
        st.rerun()

    if user_role == "admin":
        st.markdown("---")
        if st.button("👑 Quản Trị Hệ Thống", use_container_width=True, type="primary" if st.session_state.get("game_mode") == "admin" else "secondary"):
            st.session_state.game_mode = "admin"
            st.session_state['trigger_rerun'] = True

    st.markdown("---")
    st.markdown("### 🎮 Chế độ chơi & AI")
    
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        if st.button("🤖 Đấu AI", use_container_width=True, type="primary" if st.session_state.game_mode == "vs_ai" else "secondary"):
            if st.session_state.game_mode == "online_pvp" and st.session_state.room_id:
                leave_room(st.session_state.room_id, user)
            st.session_state.game_mode = "vs_ai"
            size = st.session_state.size
            st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.win_score = None
            st.session_state.show_winner_overlay = False
            st.session_state.overlay_celebrated = False
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.my_symbol = "X"
            st.session_state.is_room_creator = False
            st.session_state.elo_updated_online = False
            st.session_state.ai_stats = None
            st.session_state.ai_metrics_history = []
            st.session_state.ai_vs_ai_history = []
            st.session_state.ai_vs_ai_boards = []
            st.session_state.hint_move = None
            st.session_state.board_history = []
            st.session_state.last_move = None
            st.session_state.ai_vs_ai_running = False
            st.session_state.game_paused = False
            st.session_state.paused_elapsed_time = 0
            st.session_state.extra_paused_duration = 0
            st.session_state.turn_start_time = time.time()
            st.query_params.clear()
            st.session_state['trigger_rerun'] = True
    with c_m2:
        if st.button("🌐 Online", use_container_width=True, type="primary" if st.session_state.game_mode == "online_pvp" else "secondary"):
            st.session_state.game_mode = "online_pvp"
            st.session_state.board = []
            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.win_score = None
            st.session_state.show_winner_overlay = False
            st.session_state.overlay_celebrated = False
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.my_symbol = "X"
            st.session_state.is_room_creator = False
            st.session_state.elo_updated_online = False
            st.session_state.ai_stats = None
            st.session_state.ai_metrics_history = []
            st.session_state.ai_vs_ai_history = []
            st.session_state.ai_vs_ai_boards = []
            st.session_state.hint_move = None
            st.session_state.board_history = []
            st.session_state.last_move = None
            st.session_state.ai_vs_ai_running = False
            st.session_state.game_paused = False
            st.session_state.paused_elapsed_time = 0
            st.session_state.extra_paused_duration = 0
            st.query_params.clear()
            st.session_state['trigger_rerun'] = True

    c_m3, c_m4 = st.columns(2)
    with c_m3:
        if st.button("🤖 AI vs AI", use_container_width=True, type="primary" if st.session_state.game_mode == "ai_vs_ai" else "secondary"):
            st.session_state.game_mode = "ai_vs_ai"
            size = st.session_state.size
            st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
            st.session_state.ai_sim_board = [[" " for _ in range(size)] for _ in range(size)]
            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.ai_vs_ai_running = False
            st.session_state.ai_vs_ai_history = []
            st.session_state.ai_vs_ai_boards = []
            st.session_state.last_move = None
            st.session_state['trigger_rerun'] = True
    with c_m4:
        if st.button("📊 Thực nghiệm", use_container_width=True, type="primary" if st.session_state.game_mode == "benchmark" else "secondary"):
            st.session_state.game_mode = "benchmark"
            st.session_state['trigger_rerun'] = True

    if st.session_state.game_mode == "vs_ai":
        st.markdown("---")
        st.markdown("### ⏱️ Cấu hình thời gian lượt")
        time_options = [15, 30, 45, 60]
        current_time_limit = st.session_state.get("turn_time_limit", 30)
        time_limit_option = st.selectbox(
            "Thời gian mỗi lượt (giây):", 
            time_options, 
            index=time_options.index(current_time_limit) if current_time_limit in time_options else 1,
            label_visibility="collapsed"
        )
        if time_limit_option != st.session_state.turn_time_limit:
            st.session_state.turn_time_limit = time_limit_option
            st.session_state.turn_start_time = time.time()
            st.session_state['trigger_rerun'] = True

    if st.session_state.game_mode == "online_pvp":
        st.markdown("---")
        st.markdown("### ⏱️ Thời gian lượt Online")
        online_time_options = [0, 30, 60, 120]
        online_limit = st.session_state.get("online_turn_time_limit", 0)
        online_limit_option = st.selectbox(
            "Giới hạn thời gian:",
            online_time_options,
            index=online_time_options.index(online_limit) if online_limit in online_time_options else 0,
            format_func=lambda x: "Không giới hạn" if x == 0 else f"{x} giây",
            key="online_turn_time_select",
            label_visibility="collapsed"
        )
        st.session_state.online_turn_time_limit = online_limit_option

    st.markdown("---")
    st.markdown("### 📐 Kích thước bàn cờ")
    grid_size = st.selectbox("Chọn lưới bàn cờ:", [3, 5, 10, 12], index=[3, 5, 10, 12].index(current_size), label_visibility="collapsed")
    if grid_size != current_size:
        st.session_state.size = grid_size
        st.session_state.board = [[" " for _ in range(grid_size)] for _ in range(grid_size)]
        st.session_state.ai_sim_board = [[" " for _ in range(grid_size)] for _ in range(grid_size)]
        st.session_state.turn = "X"
        st.session_state.winner = None
        st.session_state.winning_line = []
        st.session_state.win_score = None
        st.session_state.show_winner_overlay = False
        st.session_state.overlay_celebrated = False
        st.session_state.ai_stats = None
        st.session_state.ai_metrics_history = []
        st.session_state.ai_vs_ai_history = []
        st.session_state.ai_vs_ai_boards = []
        st.session_state.hint_move = None
        st.session_state.board_history = []
        st.session_state.last_move = None
        st.session_state.ai_vs_ai_running = False
        st.session_state.game_paused = False
        st.session_state.paused_elapsed_time = 0
        st.session_state.extra_paused_duration = 0
        st.session_state.turn_start_time = time.time()
        st.session_state['trigger_rerun'] = True

    if st.session_state.game_mode == "vs_ai":
        st.markdown("---")
        st.markdown("### ⚙️ Cấu hình thuật toán AI")
        ai_difficulty = st.selectbox("Mức độ khó AI:", ["Dễ", "Trung bình", "Khó"], index=["Dễ", "Trung bình", "Khó"].index(st.session_state.ai_difficulty))
        st.session_state.ai_difficulty = ai_difficulty

    if st.session_state.game_mode == "online_pvp":
        st.markdown("---")
        st.markdown("### 🌐 Quản lý phòng")
        entered_room = st.text_input("Mã phòng", value=st.session_state.room_id)
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            if st.button("Tạo", use_container_width=True):
                new_room = entered_room.strip() if entered_room.strip() else generate_room_id()
                if get_room_info(new_room):
                    st.warning("Đã tồn tại!")
                else:
                    init_room(new_room, st.session_state.size)
                    symbol = join_room(new_room, user)
                    if symbol:
                        st.session_state.room_id = new_room
                        st.session_state.my_symbol = symbol
                        st.session_state.is_room_creator = True
                        st.query_params["room"] = new_room
                        st.success(f"Tạo xong: {new_room}")
                        st.session_state['trigger_rerun'] = True
        with c_r2:
            if st.button("Vào", use_container_width=True):
                room_id = entered_room.strip()
                if room_id:
                    room = get_room_info(room_id)
                    if room:
                        symbol = join_room(room_id, user)
                        if symbol:
                            st.session_state.room_id = room_id
                            st.session_state.my_symbol = symbol
                            st.query_params["room"] = room_id
                            st.session_state['trigger_rerun'] = True
                        else:
                            st.warning("Phòng đầy hoặc bạn đã có mặt trong phòng!")
                    else:
                        st.warning("Không thấy phòng!")
        if st.button("🚪 Rời phòng", use_container_width=True):
            leave_room(st.session_state.room_id, user)
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.my_symbol = "X"
            st.session_state.board = []
            st.session_state.replay_online_step = 0
            st.session_state.replay_online_signature = None
            st.query_params.clear()
            st.session_state['trigger_rerun'] = True

    st.markdown("---")
    with st.expander("🏆 Bảng Xếp Hạng Elo — Top 10", expanded=False):
        users = cached_get_all_users()
        if users:
            ranking_rows = []
            for idx, u in enumerate(users[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, str(idx))
                ranking_rows.append({
                    "Hạng": medal,
                    "Người chơi": u["username"],
                    "Elo": u["elo"],
                })
            st.dataframe(ranking_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu xếp hạng.")

    with st.expander("👤 Hồ sơ & Thống kê của tôi", expanded=False):
        profile_stats = get_player_stats(user)
        p1, p2 = st.columns(2)
        with p1:
            st.metric("🏆 Elo", user_score)
            st.metric("🎮 Tổng trận", profile_stats["total"])
            st.metric("🟢 Thắng", profile_stats["wins"])
        with p2:
            st.metric("⭐ Level", current_level)
            st.metric("🔴 Thua", profile_stats["losses"])
            st.metric("⚪ Hòa", profile_stats["draws"])
        st.progress(profile_stats["win_rate"] / 100 if profile_stats["total"] else 0)
        st.caption(f"📈 Tỷ lệ thắng: **{profile_stats['win_rate']}%**")

        if profile_stats["total"]:
            st.markdown("**Phân bố kết quả:**")
            st.bar_chart(
                {
                    "Số trận": [profile_stats["wins"], profile_stats["losses"], profile_stats["draws"]]
                },
                x_label="Kết quả (Thắng / Thua / Hòa)",
                y_label="Số trận"
            )

        player_matches = get_player_matches(user, 10)
        if player_matches:
            history_rows = []
            for m in player_matches:
                history_rows.append({
                    "Thời gian": m.get("timestamp", "-"),
                    "Đối thủ": m.get("opponent", "-"),
                    "Kết quả": m.get("result", "-"),
                    "Elo": m.get("score", "-")
                })
            st.markdown("**📜 10 trận gần nhất:**")
            st.dataframe(history_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có lịch sử trận đấu.")

# ================= MAIN AREA =================
if st.session_state.get("game_mode") == "admin" and user_role == "admin":
    render_admin_page()
elif st.session_state.get("game_mode") == "benchmark":
    st.markdown('<div class="main-title">📊 Thực nghiệm & So sánh Thuật toán AI</div>', unsafe_allow_html=True)
    st.markdown("So sánh chi tiết số nút duyệt và thời gian xử lý giữa **Minimax Thuần** và **Minimax + Alpha-Beta Pruning** trên các kích thước bàn cờ.")
    
    col_bm1, col_bm2 = st.columns(2)
    with col_bm1:
        bm_depth = st.slider("Độ sâu tìm kiếm (Depth):", 1, 5, 3)
    with col_bm2:
        bm_size = st.selectbox("Kích thước bàn cờ test:", [3, 5, 10, 12], index=0)

    if st.button("🚀 Chạy So Sánh Thực Nghiệm", type="primary"):
        actual_bm_depth = min(bm_depth, 2) if bm_size >= 10 else bm_depth
        if bm_size >= 10 and bm_depth > 2:
            st.warning(f"⚠️ Kích thước bàn cờ {bm_size}x{bm_size} lớn, hệ thống tự động điều chỉnh độ sâu benchmark về `Depth = 2` để đảm bảo hiệu năng tính toán thời gian thực.")

        # Chạy benchmark và lưu kết quả vào session_state.
        # st_autorefresh() làm app rerun mỗi 1 giây, nên nếu để biến result
        # cục bộ thì bảng kết quả sẽ biến mất ngay ở lần rerun tiếp theo.
        try:
            result = benchmark_algorithms(size=bm_size, depth=actual_bm_depth)
            st.session_state.benchmark_result = result
            st.session_state.benchmark_depth_used = actual_bm_depth
            st.session_state.benchmark_size_used = bm_size
        except Exception as e:
            st.session_state.benchmark_result = None
            st.error(f"❌ Không thể chạy thực nghiệm: {e}")

    # Luôn hiển thị kết quả đã lưu, kể cả sau các lần auto-refresh.
    result = st.session_state.get("benchmark_result")
    if result:
        depth_used = st.session_state.get("benchmark_depth_used", bm_depth)
        size_used = st.session_state.get("benchmark_size_used", bm_size)
        st.success(f"✅ Đã hoàn thành đo đạc thực nghiệm — Bàn {size_used}x{size_used}, Depth = {depth_used}")

        perf_table = {
            "Thuật toán": ["Minimax thuần", "Minimax + Alpha-Beta Pruning"],
            "Số nút mở rộng (Nodes)": [f"{result['pure_nodes']:,}", f"{result['ab_nodes']:,}"],
            "Thời gian thực thi (ms)": [f"{result['pure_time']:.2f} ms", f"{result['ab_time']:.2f} ms"],
            "Hiệu suất tối ưu": ["Mốc chuẩn (Baseline)", f"Giảm ~{result['node_saved_percent']}% số node"]
        }
        st.table(perf_table)

        st.markdown("#### 📊 Biểu đồ thực nghiệm")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.caption("Số node mở rộng")
            st.bar_chart({"Nodes": [result["pure_nodes"], result["ab_nodes"]]})
        with chart_col2:
            st.caption("Thời gian xử lý (ms)")
            st.bar_chart({"Thời gian (ms)": [result["pure_time"], result["ab_time"]]})

        saving_nodes = result.get("node_saved_percent", 0)
        saving_time = round((1 - result["ab_time"] / max(result["pure_time"], 0.001)) * 100, 1)
        c1, c2 = st.columns(2)
        with c1:
            st.metric("✂️ Giảm số node", f"{saving_nodes}%")
        with c2:
            st.metric("⚡ Giảm thời gian", f"{saving_time}%")
        st.info("💡 **Nhận xét cho hội đồng bảo vệ:** Minimax thuần được dùng làm baseline; Alpha-Beta Pruning giữ nguyên kết quả tìm kiếm nhưng loại bỏ nhiều nhánh không cần thiết, từ đó giảm số node và thời gian xử lý.")

elif st.session_state.get("game_mode") == "ai_vs_ai":
    st.markdown('<div class="main-title">🤖 Chế độ AI đấu với AI (Demo Tự động)</div>', unsafe_allow_html=True)
    st.markdown("Hai cấu hình AI sử dụng thuật toán **Minimax + Alpha-Beta Pruning** đối đầu trực tiếp trên bàn cờ để kiểm tra hiệu năng chiến thuật tự động.")
    
    col_aivai1, col_aivai2, col_aivai3 = st.columns(3)
    with col_aivai1:
        ai_x_diff = st.selectbox("AI (X) - Độ khó:", ["Dễ", "Trung bình", "Khó"], index=1, key="ai_x_diff_box")
    with col_aivai2:
        ai_o_diff = st.selectbox("AI (O) - Độ khó:", ["Dễ", "Trung bình", "Khó"], index=2, key="ai_o_diff_box")
    with col_aivai3:
        step_delay = st.slider("Tốc độ chạy (giây/bước):", 0.1, 2.0, 0.7, 0.1, key="ai_step_delay")

    board_size = st.session_state.size
    if "ai_sim_board" not in st.session_state or len(st.session_state.ai_sim_board) != board_size:
        st.session_state.ai_sim_board = [[" " for _ in range(board_size)] for _ in range(board_size)]
    if "ai_sim_turn" not in st.session_state:
        st.session_state.ai_sim_turn = "X"
    if "ai_sim_step" not in st.session_state:
        st.session_state.ai_sim_step = 0
    if "total_nodes_x" not in st.session_state:
        st.session_state.total_nodes_x = 0
    if "total_nodes_o" not in st.session_state:
        st.session_state.total_nodes_o = 0
    if "time_x" not in st.session_state:
        st.session_state.time_x = 0.0
    if "time_o" not in st.session_state:
        st.session_state.time_o = 0.0

    c_ctrl1, c_ctrl2, c_ctrl3 = st.columns([2, 2, 2])
    with c_ctrl1:
        if st.button("▶ Bắt đầu / Chơi lại", type="primary", use_container_width=True):
            current_board_size = st.session_state.size
            st.session_state.ai_sim_board = [[" " for _ in range(current_board_size)] for _ in range(current_board_size)]
            st.session_state.ai_sim_turn = "X"
            st.session_state.ai_sim_step = 0
            st.session_state.total_nodes_x = 0
            st.session_state.total_nodes_o = 0
            st.session_state.time_x = 0.0
            st.session_state.time_o = 0.0
            st.session_state.ai_vs_ai_history = []
            st.session_state.ai_vs_ai_boards = []
            st.session_state.ai_vs_ai_running = True
            st.session_state.last_move = None
            st.rerun()
    with c_ctrl2:
        pause_match = st.checkbox("⏸ Tạm dừng trận đấu", value=not st.session_state.ai_vs_ai_running)
        st.session_state.ai_vs_ai_running = not pause_match
    with c_ctrl3:
        if st.button("🔄 Đặt lại bàn cờ", use_container_width=True):
            current_board_size = st.session_state.size
            st.session_state.ai_sim_board = [[" " for _ in range(current_board_size)] for _ in range(current_board_size)]
            st.session_state.ai_sim_turn = "X"
            st.session_state.ai_sim_step = 0
            st.session_state.ai_vs_ai_history = []
            st.session_state.ai_vs_ai_boards = []
            st.session_state.ai_vs_ai_running = False
            st.session_state.last_move = None
            st.rerun()

    sim_board = st.session_state.ai_sim_board
    current_turn = st.session_state.ai_sim_turn

    w_final, l_final = check_winner(sim_board, board_size)
    is_board_full = is_full(sim_board, board_size)

    img_demo = draw_caro_board(sim_board, board_size, winning_line=l_final, last_move=st.session_state.last_move)
    col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
    with col_img2:
        st.image(img_demo, width=450)

    if w_final or is_board_full:
        st.session_state.ai_vs_ai_running = False
        if w_final:
            st.success(f"🏆 **Kết quả:** AI **{w_final}** giành chiến thắng thuyết phục!")
        else:
            st.info("🤝 **Kết quả:** Trận đấu kết thúc với tỷ số Hòa!")

        st.markdown("#### 📊 Bảng thống kê tổng kết trận đấu AI vs AI")
        summary_table = {
            "Chỉ số": ["Tổng số bước đi", "Tổng Nodes đã duyệt", "Tổng thời gian suy nghĩ", "Thuật toán áp dụng"],
            f"AI (X) [{ai_x_diff}]": [f"{st.session_state.ai_sim_step // 2} nước", f"{st.session_state.total_nodes_x:,} nodes", f"{st.session_state.time_x:.2f} ms", "Minimax + Alpha-Beta"],
            f"AI (O) [{ai_o_diff}]": [f"{st.session_state.ai_sim_step // 2} nước", f"{st.session_state.total_nodes_o:,} nodes", f"{st.session_state.time_o:.2f} ms", "Minimax + Alpha-Beta"]
        }
        st.table(summary_table)
    elif st.session_state.ai_vs_ai_running:
        time.sleep(step_delay)
        
        diff_to_use = ai_x_diff if current_turn == "X" else ai_o_diff
        r, c, nodes_c, t_c = ai_move(board_size, sim_board, difficulty=diff_to_use)
        
        if current_turn == "X":
            st.session_state.total_nodes_x += nodes_c
            st.session_state.time_x += t_c
        else:
            st.session_state.total_nodes_o += nodes_c
            st.session_state.time_o += t_c
            
        sim_board[r][c] = current_turn
        st.session_state.ai_vs_ai_boards.append(copy.deepcopy(sim_board))
        st.session_state.ai_vs_ai_history.append({
            "step": st.session_state.ai_sim_step + 1,
            "turn": current_turn,
            "difficulty": diff_to_use,
            "move": (r + 1, c + 1),
            "nodes": nodes_c,
            "time_ms": round(t_c, 2)
        })

        st.session_state.last_move = (r, c)
        st.session_state.ai_sim_step += 1
        st.session_state.ai_sim_turn = "O" if current_turn == "X" else "X"
        
        st.rerun()
    else:
        st.warning("⏸ Trận đấu đang tạm dừng. Bỏ tích 'Tạm dừng trận đấu' hoặc bấm '▶ Bắt đầu' để tiếp tục.")

    st.markdown("---")
    col_aivai_exp1, col_aivai_exp2 = st.columns(2)
    with col_aivai_exp1:
        with st.expander("📜 Lịch sử chi tiết các nước đi (AI vs AI)", expanded=True):
            if st.session_state.get("ai_vs_ai_history"):
                for hist in st.session_state.ai_vs_ai_history:
                    st.markdown(f"• **Bước {hist['step']}** ({hist['turn']} - {hist['difficulty']}): Hàng `{hist['move'][0]}`, Cột `{hist['move'][1]}` | ⏱️ `{hist['time_ms']} ms` | 🧠 `{hist['nodes']:,} nodes`")
            else:
                st.info("Chưa có lịch sử nước đi. Bấm '▶ Bắt đầu / Chơi lại' để chạy mô phỏng.")
    with col_aivai_exp2:
        with st.expander("📥 Xuất Dữ liệu Ván đấu AI vs AI (JSON Replay)"):
            st.markdown("Tải lịch sử các bàn cờ và nước đi mô phỏng dưới định dạng JSON:")
            if st.session_state.get("ai_vs_ai_boards"):
                replay_json_aivai = json.dumps(st.session_state.ai_vs_ai_boards, ensure_ascii=False, indent=4)
                st.download_button(
                    label="📥 Tải lịch sử AI vs AI (JSON)",
                    data=replay_json_aivai,
                    file_name="ai_vs_ai_match_replay.json",
                    mime="application/json",
                    key="download_btn_aivai"
                )
            else:
                st.info("Chưa có dữ liệu để xuất.")

else:
    st.markdown('<div class="main-title">🪵 Cờ Caro Trực Tuyến 🪵</div>', unsafe_allow_html=True)

    # ==== ONLINE PVP DATA SYNCHRONIZATION ====
    if st.session_state.get("game_mode") == "online_pvp":
        room_data = get_room_info(st.session_state.room_id)
        if room_data is None:
            st.warning("⚠️ Phòng không tồn tại hoặc đã bị xóa.")
            st.stop()
        else:
            board = room_data["board"]
            size = room_data["size"]
            turn = room_data["turn"]
            winner = room_data["winner"]
            winning_line = room_data["winning_line"]
            players = room_data["players"]
            game_ended = room_data.get("game_ended", False)
            
            # SQLite là nguồn dữ liệu chính cho Online. Đồng bộ toàn bộ trạng thái
            # sau mỗi lần Streamlit rerun.
            st.session_state.size = size
            st.session_state.board = copy.deepcopy(board)
            st.session_state.turn = turn
            st.session_state.winner = winner
            st.session_state.winning_line = copy.deepcopy(winning_line)
            st.session_state.last_move = room_data.get("last_move")

            # ĐỒNG BỘ MÃ QUÂN CỜ TRỰC TIẾP
            if players and user in players:
                st.session_state.my_symbol = players[user]

            if room_data.get("turn_start_time") is None:
                room_data["turn_start_time"] = time.time()
                save_room(st.session_state.room_id, room_data)
                room_data = get_room_info(st.session_state.room_id) or room_data

            # Chỉ một client được cập nhật ELO. Hàm update_elo_online() đã có
            # cơ chế claim nguyên tử trong SQLite để chống cộng/trừ 2 lần.
            if game_ended and winner and not room_data.get("elo_already_updated", False):
                update_elo_online(st.session_state.room_id, winner)
                room_data = get_room_info(st.session_state.room_id) or room_data
                cached_get_all_users.clear()
                cached_get_recent_matches.clear()

            if room_data.get("elo_already_updated", False):
                st.session_state.elo_updated_online = True

            # CẬP NHẬT KẾT QUẢ VÀ HIỂN THỊ OVERLAY
            if game_ended and winner:
                st.session_state.win_score = room_data.get("last_score", {}) or {}
                st.session_state.show_winner_overlay = True

                if (
                    not st.session_state.get("overlay_celebrated", False)
                    and user in st.session_state.win_score
                    and st.session_state.win_score[user] == "+15"
                ):
                    st.balloons()
                    st.session_state.overlay_celebrated = True

            room_turn_start = room_data.get("turn_start_time", time.time())
            elapsed_time = time.time() - room_turn_start
            online_limit = int(st.session_state.get("online_turn_time_limit", 0))
            remaining_time = max(0, int(online_limit - elapsed_time)) if online_limit > 0 else 0

            # Timeout Online: chỉ áp dụng khi đủ 2 người và người chơi hiện tại đang có lượt.
            if online_limit > 0 and len(players) >= 2 and not game_ended and remaining_time <= 0:
                timed_out_symbol = room_data.get("turn", "X")
                timeout_winner = "O" if timed_out_symbol == "X" else "X"
                room_data["winner"] = timeout_winner
                room_data["winning_line"] = []
                room_data["game_ended"] = True
                room_data["last_score"] = None
                save_room(st.session_state.room_id, room_data)
                update_elo_online(st.session_state.room_id, timeout_winner)
                room_data = get_room_info(st.session_state.room_id) or room_data
                winner = timeout_winner
                game_ended = True
                st.session_state.winner = winner
                st.session_state.win_score = room_data.get("last_score", {}) or {}
                st.session_state.show_winner_overlay = True
            

    else:
        board = st.session_state.board
        size = st.session_state.size
        turn = st.session_state.turn
        winner = st.session_state.winner
        winning_line = st.session_state.winning_line
        players = {user: "X"}

        if st.session_state.get("game_paused", False):
            elapsed_time = st.session_state.paused_elapsed_time
        else:
            elapsed_time = (time.time() - st.session_state.turn_start_time) + st.session_state.get("extra_paused_duration", 0)

        remaining_time = max(0, int(st.session_state.turn_time_limit - elapsed_time))

        if not winner and not st.session_state.get("game_paused", False) and remaining_time <= 0:
            if turn == "X":
                st.warning("⏰ Hết thời gian suy nghĩ! Bạn bị xử thua do quá hạn lượt đi.")
                st.session_state.winner = "O"
                current = get_user_elo(user)
                set_user_elo(user, max(100, current - 10))
                add_match_history(user, "AI Robot", "Thua (Quá giờ)", "-10")
                st.session_state.win_score = {user: "-10"}
                st.session_state.show_winner_overlay = True

    # ==== THANH HIỂN THỊ TRẠNG THÁI VÁN ĐẤU ====
    col_status1, col_status2, col_status3 = st.columns([1, 1.2, 1])
    with col_status1:
        if st.session_state.game_mode == "vs_ai":
            mode_label = f"🤖 Đấu AI ({st.session_state.ai_difficulty})"
        else:
            mode_label = f"🌐 Phòng: {st.session_state.room_id} | Bạn là: **{st.session_state.get('my_symbol', 'X')}**"
        st.info(f"**Chế độ:** {mode_label}")
    with col_status2:
        if not winner:
            if st.session_state.game_mode == "vs_ai":
                turn_str = "Bạn (X)" if turn == "X" else "🤖 Máy (O)"
                if st.session_state.get("game_paused", False):
                    st.warning(f"**{turn_str}** | ⏸ **ĐANG TẠM DỪNG**")
                else:
                    st.success(f"**{turn_str}** | ⏱️ Còn lại: **{remaining_time}s**")
            else:
                turn_str = f"Lượt: {turn}"
                online_limit = int(st.session_state.get("online_turn_time_limit", 0))
                if online_limit > 0:
                    st.success(f"**{turn_str}** | ⏱️ Còn lại: **{remaining_time}s**")
                else:
                    st.success(f"**{turn_str}** | ♾️ *Không giới hạn thời gian*")
        else:
            st.warning("**Trạng thái:** Đã kết thúc ván đấu")
    with col_status3:
        if st.session_state.game_mode == "vs_ai":
            progress_val = max(0.0, min(1.0, remaining_time / st.session_state.turn_time_limit))
            st.progress(progress_val)
        else:
            st.caption("🌐 Chế độ tự do")

    if st.session_state.get("game_paused", False):
        st.info("ℹ️ Trận đấu đang tạm dừng. Đồng hồ thời gian đã đóng băng. Bấm **'▶ Tiếp tục'** bên dưới để tiếp tục chơi.")

    if st.session_state.game_mode == "vs_ai":
        c_btn1, c_btn2, c_btn3, c_btn4 = st.columns([2, 2, 2, 2])
        
        with c_btn1:
            is_paused = st.session_state.get("game_paused", False)
            pause_label = "▶ Tiếp tục" if is_paused else "⏸ Tạm dừng"
            if st.button(pause_label, use_container_width=True, disabled=(winner is not None)):
                if not is_paused:
                    st.session_state.game_paused = True
                    st.session_state.paused_elapsed_time = (time.time() - st.session_state.turn_start_time) + st.session_state.get("extra_paused_duration", 0)
                else:
                    st.session_state.game_paused = False
                    st.session_state.extra_paused_duration = st.session_state.paused_elapsed_time
                    st.session_state.turn_start_time = time.time()
                st.rerun()

        with c_btn2:
            if st.button("💡 Gợi ý nước đi", use_container_width=True, disabled=(winner is not None or turn != "X" or st.session_state.get("game_paused", False))):
                hint_r, hint_c = get_ai_hint(current_size, st.session_state.board, human_symbol="X", ai_symbol="O")
                st.session_state.hint_move = (hint_r, hint_c)
            if st.session_state.hint_move and not st.session_state.get("game_paused", False):
                hr, hc = st.session_state.hint_move
                st.caption(f"💡 Gợi ý: Hàng {hr+1}, Cột {hc+1}")

        with c_btn3:
            can_undo = len(st.session_state.board_history) > 0 and winner is None and turn == "X" and not st.session_state.get("game_paused", False)
            if st.button("↩️ Rút cờ (Undo)", use_container_width=True, disabled=not can_undo):
                if st.session_state.board_history:
                    st.session_state.board = st.session_state.board_history.pop()
                    st.session_state.turn = "X"
                    st.session_state.hint_move = None
                    st.session_state.last_move = st.session_state.board_history[-1] if st.session_state.board_history else None
                    if st.session_state.ai_metrics_history:
                        st.session_state.ai_metrics_history.pop()
                    st.session_state.turn_start_time = time.time()
                    st.session_state.extra_paused_duration = 0
                    st.session_state['trigger_rerun'] = True

        with c_btn4:
            if st.button("🔄 Ván mới nhanh", use_container_width=True):
                st.session_state.board = [[" " for _ in range(current_size)] for _ in range(current_size)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.session_state.win_score = None
                st.session_state.show_winner_overlay = False
                st.session_state.ai_stats = None
                st.session_state.ai_metrics_history = []
                st.session_state.hint_move = None
                st.session_state.board_history = []
                st.session_state.last_move = None
                st.session_state.game_paused = False
                st.session_state.paused_elapsed_time = 0
                st.session_state.extra_paused_duration = 0
                st.session_state.turn_start_time = time.time()
                st.session_state.feedback_submitted = False
                st.session_state.feedback_game_token = None
                st.session_state['trigger_rerun'] = True

    # ==== HIỂN THỊ BÀN CỜ VÀ BẮT SỰ KIỆN CLICK ====
    if board is not None and board != []:
        board_image = draw_caro_board(board, current_size, winning_line, st.session_state.last_move)
        
        col_c1, col_c2, col_c3 = st.columns([1, 3, 1])
        with col_c2:
            coords = streamlit_image_coordinates(board_image, width=550, key=f"caro_canvas_{current_size}_{winner}")

        can_click = True
        if st.session_state.get("game_paused", False):
            can_click = False
        elif st.session_state.game_mode == "online_pvp":
            my_sym = st.session_state.get("my_symbol", "X")
            if not players or len(players) < 2 or winner is not None or user not in players or turn != my_sym:
                can_click = False
        else:
            if winner is not None or turn != "X":
                can_click = False

        if coords and can_click:
            click_x = coords["x"]
            click_y = coords["y"]
            
            rendered_w = coords.get("width", 550)
            rendered_h = coords.get("height", 550)
            
            img_size = 550
            padding = 25
            
            scaled_x = click_x * (img_size / rendered_w)
            scaled_y = click_y * (img_size / rendered_h)
            
            board_draw_size = img_size - (2 * padding)
            cell_size = board_draw_size / current_size
            
            c = int((scaled_x - padding) // cell_size)
            r = int((scaled_y - padding) // cell_size)
            
            if 0 <= r < current_size and 0 <= c < current_size:
                if board[r][c] == " ":
                    if st.session_state.game_mode == "vs_ai":
                        st.session_state.board_history.append(copy.deepcopy(st.session_state.board))
                        st.session_state.board[r][c] = "X"
                        st.session_state.hint_move = None
                        st.session_state.last_move = (r, c)
                        w, line = check_winner(st.session_state.board, current_size)
                        if w:
                            st.session_state.winner = w
                            st.session_state.winning_line = line
                            if w == "X":
                                current = get_user_elo(user)
                                set_user_elo(user, current + 15)
                                add_match_history(user, "AI Robot", "Thắng", "+15")
                                st.session_state.win_score = {user: "+15"}
                                st.balloons()
                                st.session_state.show_winner_overlay = True
                        elif is_full(st.session_state.board, current_size):
                            st.session_state.winner = "Draw"
                            st.session_state.win_score = {user: "0"}
                            add_match_history(user, "AI Robot", "Hòa", "0")
                            st.session_state.show_winner_overlay = True
                        else:
                            st.session_state.turn = "O"
                            ai_r, ai_c, nodes_count, time_taken = ai_move(current_size, st.session_state.board, difficulty=st.session_state.ai_difficulty)
                            st.session_state.ai_stats = (nodes_count, time_taken)
                            
                            turn_idx = len(st.session_state.board_history)
                            st.session_state.ai_metrics_history.append({
                                "turn": turn_idx,
                                "move": (ai_r + 1, ai_c + 1),
                                "nodes": nodes_count,
                                "time": time_taken,
                                "difficulty": st.session_state.ai_difficulty
                            })

                            st.session_state.board[ai_r][ai_c] = "O"
                            st.session_state.last_move = (ai_r, ai_c)
                            w2, line2 = check_winner(st.session_state.board, current_size)
                            if w2:
                                st.session_state.winner = w2
                                st.session_state.winning_line = line2
                                if w2 == "O":
                                    current = get_user_elo(user)
                                    set_user_elo(user, max(100, current - 10))
                                    add_match_history(user, "AI Robot", "Thua", "-10")
                                    st.session_state.win_score = {user: "-10"}
                                    st.session_state.show_winner_overlay = True
                            elif is_full(st.session_state.board, current_size):
                                st.session_state.winner = "Draw"
                                st.session_state.win_score = {user: "0"}
                                add_match_history(user, "AI Robot", "Hòa", "0")
                                st.session_state.show_winner_overlay = True
                            else:
                                st.session_state.turn = "X"
                        
                        st.session_state.turn_start_time = time.time()
                        st.session_state.extra_paused_duration = 0
                        st.session_state['trigger_rerun'] = True
                    else:
                        success, msg = apply_move(st.session_state.room_id, r, c, user)
                        if success:
                            # apply_move() đã lưu board, last_move, move_history,
                            # turn và turn_start_time xuống SQLite.
                            st.session_state['trigger_rerun'] = True
                        else:
                            st.warning(msg)

    st.markdown("---")
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        if st.session_state.get("game_mode") == "online_pvp":
            with st.expander("📊 Lịch sử nước đi phòng Online", expanded=True):
                st.markdown(f"**Danh sách các nước đi trong phòng `{st.session_state.room_id}`:**")
                room_current_data = get_room_info(st.session_state.room_id)
                move_history_list = room_current_data.get("move_history", []) if room_current_data else []
                
                if move_history_list:
                    for idx, m in enumerate(move_history_list, 1):
                        st.markdown(f"• **Bước {idx}** ({m['symbol']} - `{m['player']}`): Hàng `{m['row']}`, Cột `{m['col']}`")
                    with st.expander("▶️ Replay từng nước đi", expanded=False):
                        render_move_replay(
                            move_history_list,
                            current_size,
                            key_prefix="replay_online",
                            title="▶️ Replay ván Online"
                        )
                else:
                    st.info("💡 Chưa có nước đi nào trong phòng. Hãy bắt đầu đánh cờ để ghi nhận lịch sử!")
        else:
            with st.expander("📊 Phân tích nước đi AI & Metrics (Lịch sử ván đấu)", expanded=True):
                st.markdown("Theo dõi chi tiết hiệu năng thuật toán qua từng lượt AI:")
                
                if st.session_state.get("ai_metrics_history"):
                    total_nodes_sum = sum(m['nodes'] for m in st.session_state.ai_metrics_history)
                    total_time_sum = sum(m['time'] for m in st.session_state.ai_metrics_history)
                    avg_time = total_time_sum / len(st.session_state.ai_metrics_history)
                    
                    summary_df_data = {
                        "Chỉ số hiệu năng": ["Tổng số nước AI đi", "Tổng số Nodes đã duyệt", "Tổng thời gian suy nghĩ", "Trung bình thời gian/nước"],
                        "Giá trị đo được": [
                            f"{len(st.session_state.ai_metrics_history)} nước",
                            f"{total_nodes_sum:,} nodes",
                            f"{total_time_sum:.2f} ms",
                            f"{avg_time:.2f} ms"
                        ]
                    }
                    st.table(summary_df_data)
                    st.markdown("---")
                
                if st.session_state.get("ai_metrics_history"):
                    for idx, metric in enumerate(st.session_state.ai_metrics_history, 1):
                        st.markdown(f"**Lượt {metric['turn']} (AI - {metric['difficulty']}):**")
                        st.caption(f"• Tọa độ đánh: Hàng `{metric['move'][0]}` , Cột `{metric['move'][1]}`\n• Số nút duyệt: `{metric['nodes']:,}` nodes\n• Thời gian: `{metric['time']:.2f} ms`")
                else:
                    if st.session_state.get("winner") is not None and len(st.session_state.board_history) == 0:
                        st.warning("⏱️ Ván đấu kết thúc do **Hết thời gian lượt đi (Timeout)** trước khi thực hiện nước đi!")
                    else:
                        st.info("💡 Chưa có lịch sử tính toán. Hãy đánh nước cờ đầu tiên để AI bắt đầu ghi nhận dữ liệu phân tích!")
                
                st.markdown("---")
                st.markdown("✨ *Thuật toán Minimax kết hợp cắt tỉa Alpha-Beta Pruning và hàm lượng giá (Heuristic Evaluation) giúp tối ưu hóa không gian tìm kiếm.*")

    with col_exp2:
        with st.expander("📥 Xuất Dữ liệu Ván đấu (JSON Replay)"):
            if st.session_state.get("game_mode") == "online_pvp":
                st.markdown("Tải lịch sử nước đi của phòng Online dưới dạng JSON:")
                room_current_data = get_room_info(st.session_state.room_id)
                move_history_list = room_current_data.get("move_history", []) if room_current_data else []
                if move_history_list:
                    replay_json_online = json.dumps(move_history_list, ensure_ascii=False, indent=4)
                    st.download_button(
                        label="📥 Tải lịch sử phòng Online (JSON)",
                        data=replay_json_online,
                        file_name=f"caro_room_{st.session_state.room_id}_replay.json",
                        mime="application/json"
                    )
                else:
                    st.info("Chưa có lịch sử nước đi để xuất.")
            else:
                st.markdown("Tải lịch sử các nước đi của ván đấu hiện tại dưới dạng JSON:")
                if st.session_state.board_history:
                    replay_json = json.dumps(st.session_state.board_history, ensure_ascii=False, indent=4)
                    st.download_button(
                        label="📥 Tải lịch sử ván đấu (JSON)",
                        data=replay_json,
                        file_name="caro_match_replay.json",
                        mime="application/json"
                    )
                else:
                    st.info("Chưa có lịch sử nước đi để xuất.")

    # ================= THỐNG KÊ NGƯỜI CHƠI & ĐÁNH GIÁ =================
    # Hiển thị thường trực để người chơi không phải mở Hồ sơ ở sidebar mới thấy
    # Thắng / Thua / Hòa và tổng quan đánh giá. Form đánh giá chi tiết vẫn nằm
    # trong phần tổng kết khi ván đấu kết thúc.
    st.markdown("---")
    st.markdown("### 👤 Thành tích & ⭐ Đánh giá của bạn")

    current_profile = get_player_stats(user)
    feedback_summary = get_feedback_summary(user)

    stat_cols = st.columns(5)
    with stat_cols[0]:
        st.metric("🎮 Tổng trận", current_profile["total"])
    with stat_cols[1]:
        st.metric("🟢 Thắng", current_profile["wins"])
    with stat_cols[2]:
        st.metric("🔴 Thua", current_profile["losses"])
    with stat_cols[3]:
        st.metric("⚪ Hòa", current_profile["draws"])
    with stat_cols[4]:
        st.metric("📈 Tỷ lệ thắng", f"{current_profile['win_rate']}%")

    rating_cols = st.columns(4)
    with rating_cols[0]:
        st.metric("⭐ Điểm đánh giá", f"{feedback_summary['avg_rating']:.1f}/5" if feedback_summary["total"] else "Chưa có")
    with rating_cols[1]:
        st.metric("📝 Số đánh giá", feedback_summary["total"])
    with rating_cols[2]:
        st.metric("🌟 5 sao", feedback_summary["five_star"])
    with rating_cols[3]:
        st.metric("⚠️ 1–2 sao", feedback_summary["low_rating"])

    if current_profile["total"]:
        st.progress(current_profile["win_rate"] / 100)

    if feedback_summary["recent"]:
        with st.expander("⭐ 5 đánh giá gần nhất", expanded=False):
            rating_rows = []
            mode_labels = {
                "vs_ai": "Đấu AI",
                "online_pvp": "Online",
                "ai_vs_ai": "AI vs AI",
                "benchmark": "Thực nghiệm"
            }
            for item in feedback_summary["recent"]:
                status_text = {
                    "new": "🆕 Mới",
                    "reviewed": "✅ Đã xem",
                    "hidden": "🙈 Đã ẩn"
                }.get(item.get("status") or "new", item.get("status") or "new")
                rating_rows.append({
                    "Chế độ": mode_labels.get(item.get("game_mode"), item.get("game_mode") or "-"),
                    "Kết quả": item.get("result") or "-",
                    "Đánh giá": "⭐" * int(item.get("rating") or 0),
                    "Nhận xét": item.get("comment") or "-",
                    "Admin": item.get("admin_reply") or "-",
                    "Trạng thái": status_text,
                    "Thời gian": item.get("created_at") or "-"
                })
            st.dataframe(rating_rows, use_container_width=True, hide_index=True)
    else:
        st.info("⭐ Bạn chưa gửi đánh giá nào. Sau khi kết thúc ván đấu, biểu mẫu **Gửi đánh giá** sẽ xuất hiện bên dưới phần tổng kết.")

    if st.session_state.get("show_winner_overlay") and st.session_state.get("winner"):
        winner_sym = st.session_state.winner
        score_dict = st.session_state.win_score
        current_elo = get_user_elo(user)
        current_lvl = get_level(current_elo)

        if score_dict and user in score_dict:
            score_change = score_dict[user]
            if winner_sym == "Draw":
                title, trophy, css_class = "🤝 HÒA", "🤝", "draw"
            else:
                game_mode_val = st.session_state.get("game_mode", "vs_ai")
                my_sym_val = st.session_state.get("my_symbol", "X")
                is_win = (winner_sym == "X") if game_mode_val == "vs_ai" else (winner_sym == my_sym_val)
                if is_win:
                    title, trophy, css_class = "🎉 CHIẾN THẮNG", "🏆", ""
                else:
                    title, trophy, css_class = "😢 THẤT BẠI", "💪", "lose"

            st.markdown(f"""
                <div style="background: white; border-radius: 16px; padding: 25px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.15); max-width: 450px; margin: 15px auto; border: 1px solid #ddd;">
                    <span style="font-size: 50px; display: block; margin-bottom: 5px;">{trophy}</span>
                    <h2 style="margin: 0 0 5px; color: #2c3e50;">{title}</h2>
                    <div style="font-size: 24px; font-weight: bold; margin: 10px 0; color: #e63946;">{score_change} điểm</div>
                    <p style="color: #666; font-size: 14px;">Cấp độ hiện tại: <b>Level {current_lvl}</b> ({current_elo} pts)</p>
                </div>
            """, unsafe_allow_html=True)

            # ==== BẢNG THỐNG KÊ TỔNG KẾT VÁN ĐẤU TRONG OVERLAY ====
            st.markdown("### 📊 Thống Kê Tổng Kết Trận Đấu")
            
            if st.session_state.get("game_mode") == "online_pvp":
                room_current_data = get_room_info(st.session_state.room_id)
                move_history_list = room_current_data.get("move_history", []) if room_current_data else []
                players_map = room_current_data.get("players", {}) if room_current_data else {}
                
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("Người chiến thắng", f"{winner_sym}" if winner_sym != "Draw" else "Hòa")
                with col_s2:
                    st.metric("Tổng số nước đi", f"{len(move_history_list)} nước")
                with col_s3:
                    st.metric("Kích thước", f"{current_size}x{current_size}")

                if move_history_list:
                    st.markdown("**📜 Lịch sử chi tiết các nước đi:**")
                    table_data = [
                        {
                            "STT": i + 1,
                            "Người chơi": m.get("player", "N/A"),
                            "Ký hiệu": m.get("symbol", "N/A"),
                            "Vị trí (Hàng, Cột)": f"({m.get('row')}, {m.get('col')})"
                        }
                        for i, m in enumerate(move_history_list)
                    ]
                    st.table(table_data)
            else:
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("Kết quả", "Thắng" if winner_sym == "X" else ("Thua" if winner_sym == "O" else "Hòa"))
                with col_s2:
                    st.metric("Số nước bạn đánh", len(st.session_state.board_history))
                with col_s3:
                    st.metric("Kích thước bàn cờ", f"{current_size}x{current_size}")

            # Thành tích tổng thể sau khi kết thúc ván này.
            end_profile = get_player_stats(user)
            st.markdown("#### 🏆 Thành tích tổng thể của bạn")
            end_stats = st.columns(4)
            with end_stats[0]:
                st.metric("🟢 Thắng", end_profile["wins"])
            with end_stats[1]:
                st.metric("🔴 Thua", end_profile["losses"])
            with end_stats[2]:
                st.metric("⚪ Hòa", end_profile["draws"])
            with end_stats[3]:
                st.metric("📈 Tỷ lệ thắng", f"{end_profile['win_rate']}%")

            # ==== ĐÁNH GIÁ SAU KHI KẾT THÚC TRÒ CHƠI ====
            game_mode_feedback = st.session_state.get("game_mode", "vs_ai")
            room_id_feedback = st.session_state.get("room_id", "") if game_mode_feedback == "online_pvp" else ""
            if winner_sym == "Draw":
                feedback_result = "Hòa"
            else:
                my_sym_feedback = st.session_state.get("my_symbol", "X")
                if game_mode_feedback == "vs_ai":
                    feedback_result = "Thắng" if winner_sym == "X" else "Thua"
                else:
                    feedback_result = "Thắng" if winner_sym == my_sym_feedback else "Thua"

            # Token duy nhất cho ván hiện tại. Token được reset khi bắt đầu ván mới.
            game_token = (
                f"{game_mode_feedback}|{room_id_feedback}|{winner_sym}|"
                f"{st.session_state.get('turn_start_time', 0)}|"
                f"{len(st.session_state.get('board_history', []))}|"
                f"{len(move_history_list) if game_mode_feedback == 'online_pvp' else len(st.session_state.get('board_history', []))}"
            )
            st.session_state.feedback_game_token = game_token

            existing_feedback = get_feedback_for_game(
                user, game_mode_feedback, room_id_feedback, game_token
            )

            st.markdown("---")
            st.markdown("### ⭐ Đánh giá sau khi kết thúc trò chơi")

            if existing_feedback:
                # Hiển thị lại đánh giá đã gửi, kể cả sau khi Streamlit rerun.
                st.success("✅ Đánh giá của bạn đã được lưu thành công.")
                rating_value = int(existing_feedback.get("rating", 0))
                comment_value = existing_feedback.get("comment") or "(Không có nhận xét)"
                result_value = existing_feedback.get("result") or feedback_result
                created_value = existing_feedback.get("created_at") or ""
                admin_reply_value = existing_feedback.get("admin_reply") or ""
                feedback_status = existing_feedback.get("status") or "new"
                replied_at_value = existing_feedback.get("replied_at") or ""

                st.markdown(f"**⭐ Đánh giá của bạn:** {'⭐' * rating_value}")
                st.markdown(f"**🏆 Kết quả trận đấu:** {result_value}")
                if game_mode_feedback == "online_pvp":
                    st.markdown(f"**🌐 Phòng:** `{room_id_feedback}`")
                st.markdown(f"**📝 Nhận xét:** {comment_value}")
                if created_value:
                    st.caption(f"🕐 Đã gửi lúc: {created_value}")

                status_label = {
                    "new": "🆕 Chờ Admin xử lý",
                    "reviewed": "✅ Đã được Admin xem",
                    "hidden": "🙈 Đánh giá đã được ẩn"
                }.get(feedback_status, feedback_status)
                st.caption(f"📌 Trạng thái: {status_label}")

                if admin_reply_value:
                    st.info(f"💬 **Phản hồi từ Admin:** {admin_reply_value}")
                    if replied_at_value:
                        st.caption(f"🕐 Admin phản hồi lúc: {replied_at_value}")
                else:
                    st.caption("💬 Admin chưa phản hồi đánh giá này.")

                with st.expander("📋 Lịch sử các đánh giá của tôi"):
                    feedback_history = get_user_feedback_history(user, 10)
                    if feedback_history:
                        history_table = []
                        for item in feedback_history:
                            mode_label = {
                                "vs_ai": "Đấu AI",
                                "online_pvp": "Online",
                                "ai_vs_ai": "AI vs AI",
                                "benchmark": "Thực nghiệm"
                            }.get(item.get("game_mode"), item.get("game_mode", "N/A"))
                            history_table.append({
                                "Chế độ": mode_label,
                                "Phòng": item.get("room_id") or "-",
                                "Kết quả": item.get("result") or "-",
                                "Đánh giá": "⭐" * int(item.get("rating", 0)),
                                "Nhận xét": item.get("comment") or "-",
                                "Admin phản hồi": item.get("admin_reply") or "-",
                                "Trạng thái": item.get("status") or "new",
                                "Thời gian": item.get("created_at") or "-"
                            })
                        st.dataframe(history_table, use_container_width=True, hide_index=True)
                    else:
                        st.info("Chưa có lịch sử đánh giá nào khác.")
            else:
                with st.form("game_feedback_form", clear_on_submit=False):
                    rating = st.radio(
                        "Bạn đánh giá trải nghiệm trận đấu này thế nào?",
                        options=[1, 2, 3, 4, 5],
                        index=4,
                        horizontal=True,
                        format_func=lambda x: "⭐" * x
                    )
                    feedback_comment = st.text_area(
                        "Nhận xét (không bắt buộc):",
                        placeholder="Ví dụ: AI phản hồi nhanh, giao diện dễ sử dụng...",
                        max_chars=500
                    )
                    submit_feedback = st.form_submit_button(
                        "⭐ Gửi đánh giá", type="primary", use_container_width=True
                    )

                if submit_feedback:
                    try:
                        # Kiểm tra lần cuối để tránh double-submit do rerun/autorefresh.
                        if get_feedback_for_game(user, game_mode_feedback, room_id_feedback, game_token):
                            st.warning("⚠️ Bạn đã gửi đánh giá cho ván này.")
                        else:
                            save_game_feedback(
                                user,
                                game_mode_feedback,
                                room_id_feedback,
                                feedback_result,
                                rating,
                                feedback_comment,
                                game_token
                            )
                            st.session_state.feedback_submitted = True
                            st.session_state.feedback_game_token = game_token
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Không thể lưu đánh giá: {e}")

            col_o1, col_o2, col_o3 = st.columns([1, 2, 1])
            with col_o2:
                if st.button("🔄 Bắt đầu ván mới ngay", use_container_width=True, type="primary"):
                    size = st.session_state.size
                    new_board = [[" " for _ in range(size)] for _ in range(size)]
                    st.session_state.board = new_board
                    st.session_state.turn = "X"
                    st.session_state.winner = None
                    st.session_state.winning_line = []
                    st.session_state.win_score = None
                    st.session_state.show_winner_overlay = False
                    st.session_state.elo_updated_online = False
                    st.session_state.ai_stats = None
                    st.session_state.ai_metrics_history = []
                    st.session_state.ai_vs_ai_history = []
                    st.session_state.ai_vs_ai_boards = []
                    st.session_state.hint_move = None
                    st.session_state.board_history = []
                    st.session_state.last_move = None
                    st.session_state.game_paused = False
                    st.session_state.paused_elapsed_time = 0
                    st.session_state.extra_paused_duration = 0
                    st.session_state.turn_start_time = time.time()
                    st.session_state.feedback_submitted = False
                    st.session_state.feedback_game_token = None
                    st.session_state.replay_online_step = 0
                    st.session_state.replay_online_signature = None

                    if st.session_state.get("game_mode") != "vs_ai":
                        room_id = st.session_state.get("room_id")
                        if room_id:
                            room = get_room_info(room_id)
                            if room:
                                room["board"] = new_board
                                room["turn"] = "X"
                                room["winner"] = None
                                room["winning_line"] = []
                                room["last_score"] = None
                                room["game_ended"] = False
                                room["elo_already_updated"] = False
                                room["last_move"] = None
                                room["move_history"] = []
                                room["turn_start_time"] = time.time()
                                save_room(room_id, room)
                                st.session_state.elo_updated_online = False
                                st.session_state.overlay_celebrated = False
                                
                    st.session_state['trigger_rerun'] = True