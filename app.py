import random
import streamlit as st
import hashlib
import json
import os
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Cờ Caro Trực Tuyến", 
    page_icon="🪵", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

ROOMS_FILE = "rooms.json"

def read_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def write_rooms(rooms):
    with open(ROOMS_FILE, "w", encoding="utf-8") as f:
        json.dump(rooms, f, ensure_ascii=False, indent=2)

def get_room(room_id):
    rooms = read_rooms()
    return rooms.get(room_id)

def save_room(room_id, room_data):
    rooms = read_rooms()
    rooms[room_id] = room_data
    write_rooms(rooms)

def delete_room(room_id):
    rooms = read_rooms()
    if room_id in rooms:
        del rooms[room_id]
        write_rooms(rooms)

def init_room(room_id, size):
    rooms = read_rooms()
    if room_id in rooms:
        return False
    rooms[room_id] = {
        "board": [[" " for _ in range(size)] for _ in range(size)],
        "size": size,
        "turn": "X",
        "winner": None,
        "winning_line": [],
        "players": {},
        "last_score": None,
        "game_ended": False,
    }
    write_rooms(rooms)
    return True

def join_room(room_id, username):
    room = get_room(room_id)
    if not room:
        return None
    if username in room["players"]:
        return room["players"][username]
    if len(room["players"]) >= 2:
        return None
    symbol = "X" if len(room["players"]) == 0 else "O"
    room["players"][username] = symbol
    save_room(room_id, room)
    return symbol

def leave_room(room_id, username):
    room = get_room(room_id)
    if room and username in room["players"]:
        del room["players"][username]
        if not room["players"]:
            delete_room(room_id)
        else:
            save_room(room_id, room)

def apply_move(room_id, row, col, username):
    room = get_room(room_id)
    if not room:
        return False, "Phòng không tồn tại."
    if username not in room["players"]:
        return False, "Bạn chưa tham gia phòng."
    symbol = room["players"][username]
    if room["winner"] is not None:
        return False, "Trận đã kết thúc."
    if room["turn"] != symbol:
        return False, "Chưa đến lượt bạn."
    board = room["board"]
    size = room["size"]
    if row < 0 or row >= size or col < 0 or col >= size:
        return False, "Ô không hợp lệ."
    if board[row][col] != " ":
        return False, "Ô đã bị chiếm."
    board[row][col] = symbol
    winner, win_line = check_winner(board, size)
    if winner:
        room["winner"] = winner
        room["winning_line"] = win_line
        room["game_ended"] = True
        update_elo_online(room_id, winner)
    elif is_full(board, size):
        room["winner"] = "Draw"
        room["game_ended"] = True
        update_elo_online(room_id, "Draw")
    else:
        room["turn"] = "O" if symbol == "X" else "X"
    save_room(room_id, room)
    return True, "Thành công"

def update_elo_online(room_id, winner):
    room = get_room(room_id)
    if not room:
        return
    players = room["players"]
    if len(players) != 2:
        return
    user_list = list(players.keys())
    p1, p2 = user_list[0], user_list[1]
    s1, s2 = players[p1], players[p2]
    
    score_changes = {}
    
    if winner == "X":
        win_user = p1 if s1 == "X" else p2
        lose_user = p2 if s1 == "X" else p1
        st.session_state.users[win_user] = st.session_state.users.get(win_user, 1000) + 15
        st.session_state.users[lose_user] = max(100, st.session_state.users.get(lose_user, 1000) - 10)
        score_changes[win_user] = "+15"
        score_changes[lose_user] = "-10"
        for u in [win_user, lose_user]:
            st.session_state.match_history.append({
                "player": u,
                "opponent": lose_user if u == win_user else win_user,
                "result": "Thắng" if u == win_user else "Thua",
                "score": "+15" if u == win_user else "-10",
            })
    elif winner == "O":
        win_user = p1 if s1 == "O" else p2
        lose_user = p2 if s1 == "O" else p1
        st.session_state.users[win_user] = st.session_state.users.get(win_user, 1000) + 15
        st.session_state.users[lose_user] = max(100, st.session_state.users.get(lose_user, 1000) - 10)
        score_changes[win_user] = "+15"
        score_changes[lose_user] = "-10"
        for u in [win_user, lose_user]:
            st.session_state.match_history.append({
                "player": u,
                "opponent": lose_user if u == win_user else win_user,
                "result": "Thắng" if u == win_user else "Thua",
                "score": "+15" if u == win_user else "-10",
            })
    elif winner == "Draw":
        for u in [p1, p2]:
            st.session_state.users[u] = st.session_state.users.get(u, 1000) + 0
            st.session_state.match_history.append({
                "player": u,
                "opponent": p2 if u == p1 else p1,
                "result": "Hòa",
                "score": "0",
            })
            score_changes[u] = "0"
    
    room["last_score"] = score_changes

def check_winner(b, sz):
    win_len = 3 if sz == 3 else 5
    for r in range(sz):
        for c in range(sz - win_len + 1):
            symbol = b[r][c]
            if symbol != " " and all(b[r][c+k] == symbol for k in range(win_len)):
                return symbol, [(r, c+k) for k in range(win_len)]
    for c in range(sz):
        for r in range(sz - win_len + 1):
            symbol = b[r][c]
            if symbol != " " and all(b[r+k][c] == symbol for k in range(win_len)):
                return symbol, [(r+k, c) for k in range(win_len)]
    for r in range(sz - win_len + 1):
        for c in range(sz - win_len + 1):
            symbol = b[r][c]
            if symbol != " " and all(b[r+k][c+k] == symbol for k in range(win_len)):
                return symbol, [(r+k, c+k) for k in range(win_len)]
    for r in range(sz - win_len + 1):
        for c in range(win_len - 1, sz):
            symbol = b[r][c]
            if symbol != " " and all(b[r+k][c-k] == symbol for k in range(win_len)):
                return symbol, [(r+k, c-k) for k in range(win_len)]
    return None, []

def is_full(b, sz):
    return all(b[r][c] != " " for r in range(sz) for c in range(sz))

def ai_move(size, board):
    best_move = None
    for r in range(size):
        for c in range(size):
            if board[r][c] == " ":
                has_neighbor = any(
                    0 <= r+dr < size and 0 <= c+dc < size and board[r+dr][c+dc] != " "
                    for dr in [-1,0,1] for dc in [-1,0,1] if not (dr==0 and dc==0)
                )
                if has_neighbor or size == 3:
                    best_move = (r, c)
                    break
        if best_move:
            break
    if not best_move:
        best_move = (size//2, size//2)
    return best_move

def generate_room_id():
    return "phong_" + hashlib.md5(str(random.random()).encode()).hexdigest()[:8]

# ----------------- KHỞI TẠO SESSION STATE -----------------
if "users" not in st.session_state:
    st.session_state.users = {}
if "match_history" not in st.session_state:
    st.session_state.match_history = []
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "board" not in st.session_state:
    st.session_state.size = 10
    st.session_state.board = [[" " for _ in range(10)] for _ in range(10)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.session_state.winning_line = []
    st.session_state.game_mode = "vs_ai"
    st.session_state.room_id = "phong_mac_dinh"
    st.session_state.is_room_creator = False
    st.session_state.my_symbol = "X"
    st.session_state.win_score = None

current_size = st.session_state.size

# CSS - Chỉ 1 bàn cờ duy nhất
css_code = f"""
<style>
    .block-container {{
        padding: 0.2rem !important;
        max-width: 100% !important;
        background-color: #fcf9f2;
        border-radius: 12px;
    }}
    
    h1, h2, h3 {{
        color: #5c4033;
        font-family: 'Helvetica Neue', sans-serif;
    }}
    
    .chess-board-wrapper {{
        width: 100%;
        max-width: 500px;
        margin: 5px auto;
        background-color: #d2b48c;
        border: 3px solid #8b4513;
        padding: 3px;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(139, 69, 19, 0.2);
        overflow: hidden;
    }}
    
    .board-grid {{
        display: grid !important;
        grid-template-columns: repeat({current_size}, 1fr) !important;
        gap: 1px !important;
        background-color: #c8ad7f !important;
        width: 100% !important;
        aspect-ratio: 1 / 1 !important;
    }}
    
    .board-grid .stButton {{
        width: 100% !important;
        height: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    
    .board-grid .stButton > button {{
        width: 100% !important;
        height: 100% !important;
        min-height: 20px !important;
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 0 !important;
        border: none !important;
        background-color: #fdf5e6 !important;
        font-size: clamp(12px, 2.5vw, 22px) !important;
        font-weight: 800 !important;
        color: #2c2c2c !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        touch-action: manipulation;
        cursor: pointer;
        transition: all 0.15s ease;
        box-shadow: none !important;
    }}
    
    .board-grid .stButton > button:hover:not(:disabled) {{
        background-color: #faebd7 !important;
        transform: scale(1.05);
        z-index: 2;
    }}
    
    .board-grid .stButton > button:active:not(:disabled) {{
        transform: scale(0.92);
        background-color: #e8d5b8 !important;
    }}
    
    .board-grid .stButton > button:disabled {{
        opacity: 1;
        cursor: default;
        background-color: #fdf5e6 !important;
    }}
    
    .win-cell {{
        background-color: #4ade80 !important;
        color: #064e3b !important;
        border: 2px solid #16a34a !important;
        box-shadow: 0 0 15px rgba(74, 222, 128, 0.4) !important;
        animation: winPulse 1.2s ease-in-out infinite !important;
        font-weight: 800 !important;
        font-size: clamp(12px, 2.5vw, 22px) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        height: 100% !important;
    }}
    
    @keyframes winPulse {{
        0% {{ transform: scale(1); background-color: #4ade80; }}
        50% {{ transform: scale(1.06); background-color: #86efac; }}
        100% {{ transform: scale(1); background-color: #4ade80; }}
    }}
    
    .status-card {{
        background-color: #fffaf0;
        border-left: 4px solid #8b4513;
        padding: 6px 10px;
        border-radius: 6px;
        margin-bottom: 8px;
        text-align: center;
        font-size: clamp(11px, 1.8vw, 15px);
        color: #5c4033;
        word-break: break-word;
    }}
    
    .custom-card {{
        background-color: #ffffff;
        padding: 12px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 10px;
        border: 1px solid #eaeaea;
    }}
    
    @media (max-width: 600px) {{
        .block-container {{
            padding: 0.1rem !important;
        }}
        .chess-board-wrapper {{
            border-width: 2px;
            padding: 2px;
            border-radius: 6px;
            max-width: 100%;
        }}
        .board-grid .stButton > button {{
            font-size: clamp(8px, 1.8vw, 14px) !important;
            min-height: 16px !important;
        }}
        .win-cell {{
            font-size: clamp(8px, 1.8vw, 14px) !important;
        }}
        .status-card {{
            font-size: 10px;
            padding: 4px 6px;
        }}
        h1 {{
            font-size: 16px !important;
            margin: 2px 0 !important;
        }}
        .stButton button {{
            font-size: 11px !important;
            padding: 4px 8px !important;
            min-height: 24px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 4px 6px !important;
            font-size: 10px !important;
        }}
    }}
    
    @media (max-width: 400px) {{
        .board-grid .stButton > button {{
            font-size: clamp(6px, 1.5vw, 10px) !important;
            min-height: 12px !important;
        }}
        .win-cell {{
            font-size: clamp(6px, 1.5vw, 10px) !important;
        }}
        .chess-board-wrapper {{
            padding: 1px;
            border-width: 2px;
        }}
    }}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# ----------------- ĐĂNG NHẬP -----------------
if not st.session_state.current_user:
    st.markdown(
        "<h2 style='text-align: center; color: #5c4033; font-size: clamp(16px, 4vw, 26px);'>🪵 Cờ Caro Gỗ Trực Tuyến 🪵</h2>",
        unsafe_allow_html=True,
    )
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        st.markdown(
            "<div class='custom-card'><h3 style='margin-top:0; font-size: clamp(14px, 2.5vw, 20px);'>👤 Đăng nhập</h3><p style='margin-bottom:6px; font-size: clamp(12px, 2vw, 15px);'>Nhập tên của bạn để bắt đầu:</p></div>",
            unsafe_allow_html=True,
        )
        username_input = st.text_input("Tên hiển thị", placeholder="Nhập tên...", label_visibility="collapsed")
        if st.button("Vào Trò Chơi", use_container_width=True, type="primary"):
            if username_input.strip():
                name = username_input.strip()
                st.session_state.current_user = name
                if name not in st.session_state.users:
                    st.session_state.users[name] = 1000
                st.rerun()
            else:
                st.warning("Vui lòng nhập tên hợp lệ!")
    st.stop()

user = st.session_state.current_user
user_score = st.session_state.users.get(user, 1000)

# Header
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        f"<div style='font-size: clamp(11px, 1.8vw, 14px);'>🎮 Người chơi: <strong>{user}</strong> | ⭐ Elo: <strong>{user_score}</strong></div>",
        unsafe_allow_html=True
    )
with col_h2:
    if st.button("Đổi", use_container_width=True):
        if st.session_state.game_mode == "online_pvp" and st.session_state.room_id:
            leave_room(st.session_state.room_id, user)
        st.session_state.current_user = ""
        st.session_state.win_score = None
        st.rerun()

st.markdown(
    "<h1 style='text-align: center; margin: 2px 0 4px 0; font-size: clamp(18px, 4.5vw, 30px);'>🪵 Cờ Caro Gỗ Trực Tuyến 🪵</h1>",
    unsafe_allow_html=True,
)

# Query params
query_params = st.query_params
room_from_url = query_params.get("room", None)
if room_from_url:
    st.session_state.room_id = room_from_url

# Tab
tab1, tab2 = st.tabs(["🎮 Vào Trận Đấu", "🏆 Bảng Xếp Hạng"])

with tab2:
    col_tb1, col_tb2 = st.columns(2)
    with col_tb1:
        st.markdown("### 🏆 Top Elo")
        if not st.session_state.users:
            st.info("Chưa có người chơi.")
        else:
            sorted_users = sorted(st.session_state.users.items(), key=lambda x: x[1], reverse=True)
            for idx, (u_name, u_pts) in enumerate(sorted_users[:5], 1):
                medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
                st.markdown(f"{medal} **{u_name}** — `{u_pts} pts`")
            
            with st.expander("Xem tất cả"):
                for idx, (u_name, u_pts) in enumerate(sorted_users, 1):
                    st.markdown(f"{idx}. **{u_name}** — `{u_pts} pts`")
    with col_tb2:
        st.markdown("### 📜 Lịch sử")
        if not st.session_state.match_history:
            st.info("Chưa có trận nào.")
        else:
            for match in st.session_state.match_history[-10:]:
                color_res = "green" if match["result"] == "Thắng" else ("red" if match["result"] == "Thua" else "orange")
                st.markdown(
                    f"- {match['player']} vs {match['opponent']}: <span style='color:{color_res}; font-weight:bold;'>{match['result']}</span> (`{match['score']}`)",
                    unsafe_allow_html=True,
                )

with tab1:
    # Chọn chế độ
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button(
            "🤖 AI",
            use_container_width=True,
            type="primary" if st.session_state.game_mode == "vs_ai" else "secondary",
        ):
            if st.session_state.game_mode == "online_pvp" and st.session_state.room_id:
                leave_room(st.session_state.room_id, user)
            st.session_state.game_mode = "vs_ai"
            st.session_state.board = [[" " for _ in range(st.session_state.size)] for _ in range(st.session_state.size)]
            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.room_id = "phong_mac_dinh"
            st.session_state.is_room_creator = False
            st.session_state.my_symbol = "X"
            st.session_state.win_score = None
            st.rerun()
    with col_m2:
        if st.button(
            "🌐 Online",
            use_container_width=True,
            type="primary" if st.session_state.game_mode == "online_pvp" else "secondary",
        ):
            st.session_state.game_mode = "online_pvp"
            st.session_state.board = []
            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.win_score = None
            st.rerun()

    # Chọn kích thước (chỉ cho AI)
    if st.session_state.game_mode == "vs_ai":
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            if st.button("3x3", use_container_width=True):
                st.session_state.size = 3
                st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.session_state.win_score = None
                st.rerun()
        with col_s2:
            if st.button("10x10", use_container_width=True):
                st.session_state.size = 10
                st.session_state.board = [[" " for _ in range(10)] for _ in range(10)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.session_state.win_score = None
                st.rerun()
        with col_s3:
            if st.button("12x12", use_container_width=True):
                st.session_state.size = 12
                st.session_state.board = [[" " for _ in range(12)] for _ in range(12)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.session_state.win_score = None
                st.rerun()

    # Online PVP
    if st.session_state.game_mode == "online_pvp":
        st_autorefresh(interval=2000, key="auto_refresh")

        st.markdown("---")
        st.markdown("### 🌐 Kết nối 2 máy")
        st.info("📱 Tạo hoặc tham gia phòng, copy link gửi bạn bè.")
        
        col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
        with col_r1:
            entered_room = st.text_input("Mã phòng", value=st.session_state.room_id, label_visibility="collapsed")
        with col_r2:
            if st.button("Tạo phòng", use_container_width=True):
                new_room = entered_room.strip() if entered_room.strip() else generate_room_id()
                if get_room(new_room):
                    st.warning("Phòng đã tồn tại!")
                else:
                    if st.session_state.room_id and st.session_state.my_symbol:
                        leave_room(st.session_state.room_id, user)
                    init_room(new_room, st.session_state.size)
                    symbol = join_room(new_room, user)
                    if symbol:
                        st.session_state.room_id = new_room
                        st.session_state.my_symbol = symbol
                        st.session_state.is_room_creator = True
                        st.query_params["room"] = new_room
                        st.success(f"✅ Đã tạo: {new_room} - Bạn là {symbol}")
                        st.rerun()
        with col_r3:
            if st.button("Tham gia", use_container_width=True):
                room_id = entered_room.strip()
                if not room_id:
                    st.warning("Nhập mã phòng.")
                elif not get_room(room_id):
                    st.warning("Phòng không tồn tại.")
                else:
                    if st.session_state.room_id and st.session_state.my_symbol:
                        leave_room(st.session_state.room_id, user)
                    symbol = join_room(room_id, user)
                    if symbol is None:
                        st.warning("Phòng đã đầy!")
                    else:
                        st.session_state.room_id = room_id
                        st.session_state.my_symbol = symbol
                        st.session_state.is_room_creator = False
                        st.query_params["room"] = room_id
                        st.success(f"✅ Đã tham gia: {room_id} - Bạn là {symbol}")
                        st.rerun()

        st.markdown(f"🔗 **Mã phòng:** `{st.session_state.room_id}` (Bạn: {st.session_state.my_symbol})")

        # Lấy trạng thái phòng
        room_data = get_room(st.session_state.room_id)
        if room_data:
            board = room_data["board"]
            size = room_data["size"]
            turn = room_data["turn"]
            winner = room_data["winner"]
            winning_line = room_data.get("winning_line", [])
            players = room_data["players"]
            last_score = room_data.get("last_score", None)
            game_ended = room_data.get("game_ended", False)
            
            st.session_state.size = size
            st.session_state.board = board
            st.session_state.turn = turn
            st.session_state.winner = winner
            st.session_state.winning_line = winning_line
            
            if game_ended and last_score and winner:
                st.session_state.win_score = last_score
                for player, score in last_score.items():
                    if player == user:
                        if score == "+15":
                            st.balloons()
                            st.success(f"🎉 Bạn thắng! +15 điểm")
                        elif score == "-10":
                            st.error(f"😢 Bạn thua! -10 điểm")
                        elif score == "0":
                            st.info(f"🤝 Hòa! 0 điểm")
                        break
        else:
            st.warning("Phòng chưa được tạo hoặc đã bị xóa.")
            board = None
            size = st.session_state.size
            turn = "X"
            winner = None
            winning_line = []
            players = {}
    else:
        # AI mode
        board = st.session_state.board
        size = st.session_state.size
        turn = st.session_state.turn
        winner = st.session_state.winner
        winning_line = st.session_state.winning_line
        players = {user: "X"}
        
        if winner == "X":
            st.session_state.win_score = {user: "+15"}
            st.balloons()
            st.success(f"🎉 Bạn thắng! +15 điểm")
        elif winner == "O":
            st.session_state.win_score = {user: "-10"}
            st.error(f"😢 Bạn thua! -10 điểm")
        elif winner == "Draw":
            st.session_state.win_score = {user: "0"}
            st.info(f"🤝 Hòa! 0 điểm")

    # ----------------- HIỂN THỊ TRẠNG THÁI -----------------
    mode_text = "AI" if st.session_state.game_mode == "vs_ai" else "Online"
    if not winner:
        if st.session_state.game_mode == "vs_ai":
            turn_msg = f"Lượt: <b>{'Bạn (X)' if turn == 'X' else 'Máy (O)'}</b>"
        else:
            if turn == st.session_state.my_symbol:
                turn_msg = f"Lượt: <b>Bạn ({turn})</b>"
            else:
                turn_msg = f"Lượt: <b>Đối thủ ({turn})</b>"
    else:
        turn_msg = "🏁 Trận đấu đã kết thúc!"

    st.markdown(
        f"<div class='status-card'>🎮 {mode_text} | Phòng: <code>{st.session_state.room_id}</code> | {turn_msg}</div>",
        unsafe_allow_html=True,
    )

    # ----------------- BÀN CỜ - CHỈ 1 BÀN CỜ -----------------
    if board is not None:
        st.markdown('<div class="chess-board-wrapper"><div class="board-grid">', unsafe_allow_html=True)
        
        for r in range(size):
            cols = st.columns(size)
            for c in range(size):
                val = board[r][c]
                label = val if val != " " else ""
                is_winning_cell = (r, c) in winning_line
                
                disabled = False
                if st.session_state.game_mode == "online_pvp":
                    if not players or winner is not None:
                        disabled = True
                    elif st.session_state.my_symbol not in players.values():
                        disabled = True
                    elif turn != st.session_state.my_symbol:
                        disabled = True
                    elif val != " ":
                        disabled = True
                else:
                    if winner is not None or val != " " or turn != "X":
                        disabled = True
                
                with cols[c]:
                    if is_winning_cell:
                        st.markdown(
                            f'<div class="win-cell">{label if label else " "}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        if st.button(
                            label if label else " ",
                            key=f"cell_{r}_{c}",
                            disabled=disabled,
                            use_container_width=True
                        ):
                            if st.session_state.game_mode == "vs_ai":
                                st.session_state.board[r][c] = "X"
                                w, line = check_winner(st.session_state.board, size)
                                if w:
                                    st.session_state.winner = w
                                    st.session_state.winning_line = line
                                    if w == "X":
                                        st.session_state.users[user] = st.session_state.users.get(user, 1000) + 15
                                        st.session_state.match_history.append({
                                            "player": user,
                                            "opponent": "AI Robot",
                                            "result": "Thắng",
                                            "score": "+15",
                                        })
                                        st.session_state.win_score = {user: "+15"}
                                elif is_full(st.session_state.board, size):
                                    st.session_state.winner = "Draw"
                                    st.session_state.win_score = {user: "0"}
                                else:
                                    st.session_state.turn = "O"
                                    ai_r, ai_c = ai_move(size, st.session_state.board)
                                    st.session_state.board[ai_r][ai_c] = "O"
                                    w2, line2 = check_winner(st.session_state.board, size)
                                    if w2:
                                        st.session_state.winner = w2
                                        st.session_state.winning_line = line2
                                        if w2 == "O":
                                            st.session_state.users[user] = max(100, st.session_state.users.get(user, 1000) - 10)
                                            st.session_state.match_history.append({
                                                "player": user,
                                                "opponent": "AI Robot",
                                                "result": "Thua",
                                                "score": "-10",
                                            })
                                            st.session_state.win_score = {user: "-10"}
                                    elif is_full(st.session_state.board, size):
                                        st.session_state.winner = "Draw"
                                        st.session_state.win_score = {user: "0"}
                                    else:
                                        st.session_state.turn = "X"
                                st.rerun()
                            else:
                                success, msg = apply_move(st.session_state.room_id, r, c, user)
                                if success:
                                    st.rerun()
                                else:
                                    st.warning(msg)
        
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("Chưa có bàn cờ. Hãy tạo hoặc tham gia phòng.")

    # Thông báo kết quả
    if winner:
        if winner == "X":
            st.success("🎉 Người chơi X chiến thắng!")
        elif winner == "O":
            st.success("🎉 Người chơi O chiến thắng!")
        elif winner == "Draw":
            st.warning("🤝 Trận đấu hòa!")

    # Nút chơi lại
    r_col1, r_col2, r_col3 = st.columns([1, 2, 1])
    with r_col2:
        if st.button("🔄 Ván Mới", use_container_width=True, type="primary"):
            if st.session_state.game_mode == "vs_ai":
                st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.session_state.win_score = None
            else:
                room_id = st.session_state.room_id
                room = get_room(room_id)
                if room:
                    room["board"] = [[" " for _ in range(size)] for _ in range(size)]
                    room["turn"] = "X"
                    room["winner"] = None
                    room["winning_line"] = []
                    room["last_score"] = None
                    room["game_ended"] = False
                    save_room(room_id, room)
                    st.session_state.win_score = None
            st.rerun()
