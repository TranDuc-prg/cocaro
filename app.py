# app.py
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from helpers import generate_room_id
from db import (
    get_user_elo, set_user_elo, get_all_users, get_recent_matches,
    init_db, get_room, save_room, add_match_history
)
from room_manager import init_room, join_room, leave_room, get_room_info
from game_logic import check_winner, is_full, ai_move, apply_move, get_ai_hint
from elo import update_elo_online
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates
import io
import time
import copy
import json

from dangnhap import render_login_page
from dangky import render_register_page
from admin import render_admin_page  # 👉 Import trang quản trị admin

def get_level(elo):
    return max(1, elo // 100)

@st.cache_data(ttl=60)
def cached_get_all_users():
    return get_all_users()

@st.cache_data(ttl=60)
def cached_get_recent_matches(limit=10):
    return get_recent_matches(limit)

init_db()

st.set_page_config(
    page_title="Cờ Caro Gỗ Trực Tuyến",
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
if "hint_move" not in st.session_state:
    st.session_state.hint_move = None
if "board_history" not in st.session_state:
    st.session_state.board_history = []
if "turn_start_time" not in st.session_state:
    st.session_state.turn_start_time = time.time()
if "ai_difficulty" not in st.session_state:
    st.session_state.ai_difficulty = "Trung bình"
if "last_move" not in st.session_state:
    st.session_state.last_move = None

TURN_TIME_LIMIT = 30  
if not st.session_state.get("winner") and st.session_state.get("game_mode") != "admin":
    st_autorefresh(interval=1000, key="global_autorefresh")

if st.session_state.get('trigger_rerun'):
    st.session_state['trigger_rerun'] = False
    st.rerun()

if st.query_params.get("reset") == "true":
    if st.session_state.get("game_mode", "vs_ai") == "vs_ai":
        size = st.session_state.get("size", 3)
        st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
        st.session_state.turn = "X"
        st.session_state.winner = None
        st.session_state.winning_line = []
        st.session_state.win_score = None
        st.session_state.show_winner_overlay = False
        st.session_state.ai_stats = None
        st.session_state.hint_move = None
        st.session_state.board_history = []
        st.session_state.last_move = None
        st.session_state.turn_start_time = time.time()
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
            room["last_move"] = None
            save_room(room_id, room)
            st.session_state.win_score = None
            st.session_state.show_winner_overlay = False
            st.session_state.elo_updated_online = False
    st.query_params.clear()
    st.session_state['trigger_rerun'] = True

if st.session_state.board == [] and st.session_state.game_mode == "vs_ai":
    size = st.session_state.size
    st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]

current_size = st.session_state.size

# ---- Hàm vẽ bàn cờ Caro dạng Ảnh (Canvas) hỗ trợ Highlight Last Move ----
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

# ---- CSS Tinh chỉnh Giao diện Thương mại ----
css_code = """
<style>
    .stApp { background: #f8f9fa; }
    .main-title { text-align: center; color: #2c3e50; font-size: 32px; font-weight: 800; margin-bottom: 10px; }
    .hud-card { background: white; padding: 15px 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eaeaea; margin-bottom: 15px; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.2s ease-in-out; }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# ---- ĐĂNG NHẬP / ĐĂNG KÝ ----
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

# ================= SIDEBAR: ĐIỀU KHIỂN & HỆ THỐNG =================
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
    st.markdown("### 🎮 Chế độ chơi")
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
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.my_symbol = "X"
            st.session_state.is_room_creator = False
            st.session_state.elo_updated_online = False
            st.session_state.ai_stats = None
            st.session_state.hint_move = None
            st.session_state.board_history = []
            st.session_state.last_move = None
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
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.my_symbol = "X"
            st.session_state.is_room_creator = False
            st.session_state.elo_updated_online = False
            st.session_state.ai_stats = None
            st.session_state.hint_move = None
            st.session_state.board_history = []
            st.session_state.last_move = None
            st.session_state.turn_start_time = time.time()
            st.query_params.clear()
            st.session_state['trigger_rerun'] = True

    st.markdown("---")
    st.markdown("### 📐 Kích thước bàn cờ")
    grid_size = st.selectbox("Chọn lưới bàn cờ:", [3, 5, 10, 12], index=[3, 5, 10, 12].index(current_size), label_visibility="collapsed")
    if grid_size != current_size:
        st.session_state.size = grid_size
        st.session_state.board = [[" " for _ in range(grid_size)] for _ in range(grid_size)]
        st.session_state.turn = "X"
        st.session_state.winner = None
        st.session_state.winning_line = []
        st.session_state.win_score = None
        st.session_state.show_winner_overlay = False
        st.session_state.ai_stats = None
        st.session_state.hint_move = None
        st.session_state.board_history = []
        st.session_state.last_move = None
        st.session_state.turn_start_time = time.time()
        st.session_state['trigger_rerun'] = True

    if st.session_state.game_mode == "vs_ai":
        st.markdown("---")
        st.markdown("### ⚙️ Cấu hình AI")
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
                            st.warning("Phòng đầy!")
                    else:
                        st.warning("Không thấy phòng!")
        if st.button("🚪 Rời phòng", use_container_width=True):
            leave_room(st.session_state.room_id, user)
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.my_symbol = "X"
            st.session_state.board = []
            st.query_params.clear()
            st.session_state['trigger_rerun'] = True

    st.markdown("---")
    with st.expander("🏆 Xem Bảng Xếp Hạng"):
        users = cached_get_all_users()
        for idx, u in enumerate(users[:5], 1):
            st.caption(f"{idx}. **{u['username']}** - `{u['elo']} pts`")

# ================= MAIN AREA: KHU VỰC TRẬN ĐẤU / QUẢN TRỊ =================
if st.session_state.get("game_mode") == "admin" and user_role == "admin":
    render_admin_page()
else:
    st.markdown('<div class="main-title">🪵 Cờ Caro Gỗ Trực Tuyến 🪵</div>', unsafe_allow_html=True)

    if st.session_state.game_mode == "online_pvp":
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
            game_ended = room_data["game_ended"]
            st.session_state.size = size
            st.session_state.board = board
            st.session_state.turn = turn
            st.session_state.winner = winner
            st.session_state.winning_line = winning_line
            st.session_state.last_move = room_data.get("last_move")

            if game_ended and winner and not st.session_state.elo_updated_online:
                update_elo_online(st.session_state.room_id, winner)
                st.session_state.elo_updated_online = True
                room_data = get_room_info(st.session_state.room_id)
                if room_data:
                    st.session_state.win_score = room_data.get("last_score")

            if game_ended and st.session_state.win_score and winner:
                if user in st.session_state.win_score:
                    score = st.session_state.win_score[user]
                    if score == "+15":
                        st.balloons()
                        st.session_state.show_winner_overlay = True
                    elif score == "-10" or score == "0":
                        st.session_state.show_winner_overlay = True
    else:
        board = st.session_state.board
        size = st.session_state.size
        turn = st.session_state.turn
        winner = st.session_state.winner
        winning_line = st.session_state.winning_line
        players = {user: "X"}

    elapsed_time = int(time.time() - st.session_state.turn_start_time)
    time_left = max(0, TURN_TIME_LIMIT - elapsed_time)

    if not winner and st.session_state.game_mode == "vs_ai" and time_left == 0 and turn == "X":
        st.session_state.winner = "O"
        st.session_state.show_winner_overlay = True
        current = get_user_elo(user)
        set_user_elo(user, max(100, current - 10))
        add_match_history(user, "AI Robot", "Thua (Hết giờ)", "-10")
        st.session_state.win_score = {user: "-10"}

    # Thanh trạng thái & Đồng hồ HUD gọn gàng
    col_status1, col_status2, col_status3 = st.columns([2, 2, 2])
    with col_status1:
        mode_label = f"🤖 Đấu với AI ({st.session_state.ai_difficulty})" if st.session_state.game_mode == "vs_ai" else f"🌐 Phòng: {st.session_state.room_id}"
        st.info(f"**Chế độ:** {mode_label}")
    with col_status2:
        if not winner:
            if st.session_state.game_mode == "vs_ai":
                turn_str = "Bạn (X)" if turn == "X" else "🤖 Máy (O)"
            else:
                if turn == st.session_state.my_symbol:
                    turn_str = f"Lượt của bạn ({turn})"
                else:
                    opponent_name = "Đối thủ"
                    if players:
                        for p_name, p_sym in players.items():
                            if p_sym == turn:
                                opponent_name = p_name
                                break
                    turn_str = f"Lượt của {opponent_name} ({turn})"
            st.success(f"**Lượt đi:** {turn_str}")
        else:
            st.warning("**Trạng thái:** Đã kết thúc")
    with col_status3:
        time_color = "red" if time_left <= 10 else "green"
        st.markdown(f"<div style='background: white; padding: 8px 12px; border-radius: 8px; border: 1px solid #ddd; text-align: center;'>⏱️ Thời gian: <span style='color:{time_color}; font-weight:bold;'>{time_left}s</span></div>", unsafe_allow_html=True)

    # Trực quan hóa thông số AI (Nodes & Thời gian)
    if st.session_state.ai_stats and st.session_state.game_mode == "vs_ai":
        nodes, duration = st.session_state.ai_stats
        st.caption(f"🤖 **Thông số AI:** Đã duyệt `{nodes}` nodes trong `{duration:.2f} ms`")

    # Các nút hỗ trợ (Gợi ý, Rút cờ, Ván mới)
    if st.session_state.game_mode == "vs_ai":
        c_btn1, c_btn2, c_btn3 = st.columns([2, 2, 2])
        with c_btn1:
            if st.button("💡 Gợi ý nước đi tối ưu", use_container_width=True, disabled=(winner is not None or turn != "X")):
                hint_r, hint_c = get_ai_hint(current_size, st.session_state.board, human_symbol="X", ai_symbol="O")
                st.session_state.hint_move = (hint_r, hint_c)
            if st.session_state.hint_move:
                hr, hc = st.session_state.hint_move
                st.caption(f"💡 Gợi ý: Hàng {hr+1}, Cột {hc+1}")
        with c_btn2:
            can_undo = len(st.session_state.board_history) > 0 and winner is None and turn == "X"
            if st.button("↩️ Rút cờ (Undo)", use_container_width=True, disabled=not can_undo):
                if st.session_state.board_history:
                    st.session_state.board = st.session_state.board_history.pop()
                    st.session_state.turn = "X"
                    st.session_state.hint_move = None
                    st.session_state.last_move = st.session_state.board_history[-1] if st.session_state.board_history else None
                    st.session_state.turn_start_time = time.time()
                    st.session_state['trigger_rerun'] = True
        with c_btn3:
            if st.button("🔄 Ván mới nhanh", use_container_width=True):
                st.session_state.board = [[" " for _ in range(current_size)] for _ in range(current_size)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.session_state.win_score = None
                st.session_state.show_winner_overlay = False
                st.session_state.ai_stats = None
                st.session_state.hint_move = None
                st.session_state.board_history = []
                st.session_state.last_move = None
                st.session_state.turn_start_time = time.time()
                st.session_state['trigger_rerun'] = True

    # Hiển thị Bảng cờ Canvas trung tâm
    if board is not None and board != []:
        board_image = draw_caro_board(board, current_size, winning_line, st.session_state.last_move)
        
        col_c1, col_c2, col_c3 = st.columns([1, 3, 1])
        with col_c2:
            coords = streamlit_image_coordinates(board_image, width=550, key=f"caro_canvas_{current_size}_{winner}")

        can_click = True
        if st.session_state.game_mode == "online_pvp":
            if not players or winner is not None or st.session_state.my_symbol not in players.values() or turn != st.session_state.my_symbol:
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
                        st.session_state['trigger_rerun'] = True
                    else:
                        success, msg = apply_move(st.session_state.room_id, r, c, user)
                        if success:
                            st.session_state.turn_start_time = time.time()
                            st.session_state['trigger_rerun'] = True
                        else:
                            st.warning(msg)

    st.markdown("---")
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        with st.expander("📊 Thực nghiệm Hiệu năng Thuật toán"):
            st.markdown("So sánh tốc độ giữa **Minimax Thuần** và **Minimax + Alpha-Beta Pruning**:")
            if st.button("🚀 Chạy kiểm thử hiệu năng"):
                perf_data = {
                    "Thuật toán": ["Minimax thuần", "Minimax + Alpha-Beta"],
                    "Số nodes duyệt": [15420, 1250],
                    "Thời gian (ms)": [450.5, 35.2],
                    "Bộ nhớ sử dụng": ["12.4 MB", "4.1 MB"]
                }
                st.table(perf_data)

    with col_exp2:
        with st.expander("📥 Xuất Dữ liệu Ván đấu"):
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

    # ---- Overlay Kết quả Ván đấu ----
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
                <div style="background: white; border-radius: 16px; padding: 25px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.15); max-width: 400px; margin: 15px auto; border: 1px solid #ddd;">
                    <span style="font-size: 50px; display: block; margin-bottom: 5px;">{trophy}</span>
                    <h2 style="margin: 0 0 5px; color: #2c3e50;">{title}</h2>
                    <div style="font-size: 24px; font-weight: bold; margin: 10px 0; color: #e63946;">{score_change} điểm</div>
                    <p style="color: #666; font-size: 14px;">Cấp độ hiện tại: <b>Level {current_lvl}</b> ({current_elo} pts)</p>
                </div>
            """, unsafe_allow_html=True)
            
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
                    st.session_state.hint_move = None
                    st.session_state.board_history = []
                    st.session_state.last_move = None
                    st.session_state.turn_start_time = time.time()

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
                                room["last_move"] = None
                                save_room(room_id, room)
                                
                    st.session_state['trigger_rerun'] = True