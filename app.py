import random
import streamlit as st
import hashlib

st.set_page_config(
    page_title="Cờ Caro Gỗ Trực Tuyến", page_icon="🪵", layout="centered"
)

# ----------------- BỘ NHỚ CHIA SẺ CHO PHÒNG ONLINE (dùng cache_resource) -----------------
@st.cache_resource(ttl=3600)
def get_shared_state():
    """
    Lưu trạng thái các phòng để nhiều session có thể cùng truy cập.
    Mỗi phòng lưu: board, size, turn, winner, winning_line, players (dict user->symbol), room_id
    """
    return {
        # room_id: {
        #   "board": [...],
        #   "size": int,
        #   "turn": "X" or "O",
        #   "winner": None or "X" or "O" or "Draw",
        #   "winning_line": [],
        #   "players": { "username": "X" or "O" }
        # }
    }

shared_rooms = get_shared_state()

# Khởi tạo session state
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
    st.session_state.is_room_creator = False  # True nếu người dùng tạo phòng
    st.session_state.my_symbol = "X"         # "X" hoặc "O" hoặc ""
    st.session_state.opponent = ""

# Hàm tạo mã phòng duy nhất (đơn giản)
def generate_room_id():
    return "phong_" + hashlib.md5(str(random.random()).encode()).hexdigest()[:8]

# ----------------- CSS -----------------
current_size = st.session_state.size
css_code = f"""
<style>
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 850px;
    background-color: #fcf9f2;
    border-radius: 16px;
}}
h1, h2, h3 {{
    color: #5c4033;
    font-family: 'Helvetica Neue', sans-serif;
}}
.chess-board-wrapper {{
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: #d2b48c;
    border: 5px solid #8b4513;
    padding: 8px;
    width: max-content;
    margin: 15px auto;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(139, 69, 19, 0.25);
}}
.chess-board-wrapper div[data-testid="stHorizontalBlock"] {{
    display: grid !important;
    grid-template-columns: repeat({current_size}, 40px) !important;
    gap: 0px !important;
    width: max-content !important;
    margin: 0 !important;
}}
.chess-board-wrapper div[data-testid="column"] {{
    width: 40px !important;
    flex: unset !important;
    min-width: unset !important;
    padding: 0 !important;
}}
.chess-board-wrapper div.stButton > button {{
    width: 40px !important;
    height: 40px !important;
    font-size: 18px;
    font-weight: 800;
    border-radius: 0px !important;
    border: 1px solid #c8ad7f !important;
    margin: 0 !important;
    background-color: #fdf5e6;
    color: #2c2c2c;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.1s ease;
}}
.chess-board-wrapper div.stButton > button:hover {{
    border-color: #5c4033 !important;
    background-color: #faebd7;
    transform: scale(1.02);
    z-index: 2;
}}
.win-cell button {{
    background-color: #ffe066 !important;
    color: #d9480f !important;
    border: 2px solid #f59f00 !important;
    animation: pulse 1s infinite alternate;
}}
@keyframes pulse {{
    0% {{ transform: scale(1); }}
    100% {{ transform: scale(1.08); background-color: #ffec99 !important; }}
}}
.custom-card {{
    background-color: #ffffff;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 20px;
    border: 1px solid #eaeaea;
}}
.status-card {{
    background-color: #fffaf0;
    border-left: 5px solid #8b4513;
    padding: 10px 15px;
    border-radius: 6px;
    margin-bottom: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    text-align: center;
    font-size: 16px;
    color: #5c4033;
}}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# ----------------- XỬ LÝ PHÒNG ONLINE -----------------
def init_room(room_id, size):
    """Tạo phòng mới với kích thước size, trả về True nếu tạo thành công."""
    if room_id in shared_rooms:
        return False  # phòng đã tồn tại
    shared_rooms[room_id] = {
        "board": [[" " for _ in range(size)] for _ in range(size)],
        "size": size,
        "turn": "X",  # X đi trước
        "winner": None,
        "winning_line": [],
        "players": {},  # dict username -> symbol
    }
    return True

def join_room(room_id, username):
    """Tham gia phòng, trả về symbol nếu thành công, None nếu thất bại."""
    if room_id not in shared_rooms:
        return None
    room = shared_rooms[room_id]
    # Kiểm tra nếu người chơi đã ở trong phòng rồi
    if username in room["players"]:
        return room["players"][username]
    # Nếu phòng chưa đầy (tối đa 2)
    if len(room["players"]) >= 2:
        return None  # phòng đã đầy
    # Phân công symbol: người đầu tiên là X, người thứ hai là O
    symbol = "X" if len(room["players"]) == 0 else "O"
    room["players"][username] = symbol
    return symbol

def leave_room(room_id, username):
    """Rời phòng (khi chuyển người chơi hoặc reset)."""
    if room_id in shared_rooms:
        room = shared_rooms[room_id]
        if username in room["players"]:
            del room["players"][username]
        # Nếu phòng trống thì xóa phòng
        if not room["players"]:
            del shared_rooms[room_id]

def apply_move(room_id, row, col, username):
    """Áp dụng nước đi cho người dùng trong phòng. Trả về (thành công, thông báo)."""
    if room_id not in shared_rooms:
        return False, "Phòng không tồn tại."
    room = shared_rooms[room_id]
    if username not in room["players"]:
        return False, "Bạn chưa tham gia phòng này."
    symbol = room["players"][username]
    if room["winner"] is not None:
        return False, "Trận đấu đã kết thúc."
    if room["turn"] != symbol:
        return False, "Chưa đến lượt của bạn."
    board = room["board"]
    size = room["size"]
    if row < 0 or row >= size or col < 0 or col >= size:
        return False, "Ô không hợp lệ."
    if board[row][col] != " ":
        return False, "Ô đã bị chiếm."
    # Đánh dấu
    board[row][col] = symbol
    # Kiểm tra thắng
    winner, win_line = check_winner(board, size)
    if winner:
        room["winner"] = winner
        room["winning_line"] = win_line
        # Cập nhật điểm Elo cho cả hai người chơi
        update_elo_online(room_id, winner)
        # Cập nhật lịch sử cho người chơi này (sẽ làm sau)
    elif is_full(board, size):
        room["winner"] = "Draw"
        # Cập nhật Elo hòa
        update_elo_online(room_id, "Draw")
    else:
        # Chuyển lượt
        room["turn"] = "O" if symbol == "X" else "X"
    return True, "Thành công"

def update_elo_online(room_id, winner):
    """Cập nhật điểm Elo cho cả hai người trong phòng online."""
    room = shared_rooms.get(room_id)
    if not room:
        return
    players = room["players"]
    if len(players) != 2:
        return
    user_list = list(players.keys())
    p1, p2 = user_list[0], user_list[1]
    s1, s2 = players[p1], players[p2]
    # Người thắng
    if winner == "X":
        win_user = p1 if s1 == "X" else p2
        lose_user = p2 if s1 == "X" else p1
        st.session_state.users[win_user] = st.session_state.users.get(win_user, 1000) + 15
        st.session_state.users[lose_user] = max(100, st.session_state.users.get(lose_user, 1000) - 10)
        # Lưu lịch sử cho từng người
        for u in [win_user, lose_user]:
            if u not in st.session_state.match_history:
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
        for u in [win_user, lose_user]:
            if u not in st.session_state.match_history:
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

# ----------------- HÀM KIỂM TRA THẮNG -----------------
def check_winner(b, sz):
    win_len = 3 if sz == 3 else 5
    # Ngang
    for r in range(sz):
        for c in range(sz - win_len + 1):
            symbol = b[r][c]
            if symbol != " " and all(b[r][c + k] == symbol for k in range(win_len)):
                return symbol, [(r, c + k) for k in range(win_len)]
    # Dọc
    for c in range(sz):
        for r in range(sz - win_len + 1):
            symbol = b[r][c]
            if symbol != " " and all(b[r + k][c] == symbol for k in range(win_len)):
                return symbol, [(r + k, c) for k in range(win_len)]
    # Chéo chính
    for r in range(sz - win_len + 1):
        for c in range(sz - win_len + 1):
            symbol = b[r][c]
            if symbol != " " and all(b[r + k][c + k] == symbol for k in range(win_len)):
                return symbol, [(r + k, c + k) for k in range(win_len)]
    # Chéo phụ
    for r in range(sz - win_len + 1):
        for c in range(win_len - 1, sz):
            symbol = b[r][c]
            if symbol != " " and all(b[r + k][c - k] == symbol for k in range(win_len)):
                return symbol, [(r + k, c - k) for k in range(win_len)]
    return None, []

def is_full(b, sz):
    return all(b[r][c] != " " for r in range(sz) for c in range(sz))

# ----------------- AI (đơn giản) -----------------
def ai_move(size, board):
    # Tìm ô trống gần quân cờ nhất
    best_move = None
    for r in range(size):
        for c in range(size):
            if board[r][c] == " ":
                has_neighbor = any(
                    0 <= r + dr < size and 0 <= c + dc < size and board[r + dr][c + dc] != " "
                    for dr in [-1, 0, 1] for dc in [-1, 0, 1] if not (dr == 0 and dc == 0)
                )
                if has_neighbor or size == 3:
                    best_move = (r, c)
                    break
        if best_move:
            break
    if not best_move:
        # Nếu bàn trống, đi giữa
        best_move = (size // 2, size // 2)
    return best_move

# ----------------- XỬ LÝ ĐĂNG NHẬP -----------------
if not st.session_state.current_user:
    st.markdown(
        "<h2 style='text-align: center; color: #5c4033;'>🪵 Cờ Caro Gỗ Trực"
        " Tuyến 🪵</h2>",
        unsafe_allow_html=True,
    )
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        st.markdown(
            "<div class='custom-card'><h3>👤 Đăng nhập người chơi</h3><p>Vui lòng nhập tên của bạn để bắt đầu trò chơi:</p></div>",
            unsafe_allow_html=True,
        )
        username_input = st.text_input("Tên hiển thị", placeholder="Nhập tên của bạn...")
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

# ----------------- HEADER -----------------
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(f"🎮 Người chơi: **{user}** | ⭐ Điểm Elo: **`{user_score}`**", unsafe_allow_html=True)
with col_h2:
    if st.button("Đổi người chơi"):
        # Rời phòng nếu đang ở online
        if st.session_state.game_mode == "online_pvp" and st.session_state.room_id:
            leave_room(st.session_state.room_id, user)
        st.session_state.current_user = ""
        st.rerun()

st.markdown(
    "<h1 style='text-align: center; margin-top: 5px;'>🪵 Cờ Caro Gỗ Trực Tuyến 🪵</h1>",
    unsafe_allow_html=True,
)

# ----------------- QUERY PARAMS PHÒNG -----------------
query_params = st.query_params
room_from_url = query_params.get("room", None)
if room_from_url:
    st.session_state.room_id = room_from_url

# ----------------- TAB -----------------
tab1, tab2 = st.tabs(["🎮 Vào Trận Đấu", "🏆 Bảng Xếp Hạng & Lịch Sử"])

with tab2:
    col_tb1, col_tb2 = st.columns(2)
    with col_tb1:
        st.markdown("### 🏆 Top Điểm Elo Cao Nhất")
        if not st.session_state.users:
            st.info("Chưa có người chơi nào trên bảng xếp hạng.")
        else:
            sorted_users = sorted(st.session_state.users.items(), key=lambda x: x[1], reverse=True)
            for idx, (u_name, u_pts) in enumerate(sorted_users[:5], 1):
                medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
                st.markdown(f"{medal} **{u_name}** — `{u_pts} pts`")
    with col_tb2:
        st.markdown("### 📜 Lịch sử đấu gần đây")
        if not st.session_state.match_history:
            st.info("Chưa có trận đấu nào.")
        else:
            for match in st.session_state.match_history[-5:]:
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
            "🤖 Đấu với Máy (AI)",
            use_container_width=True,
            type="primary" if st.session_state.game_mode == "vs_ai" else "secondary",
        ):
            # Rời phòng online nếu đang ở đó
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
            st.rerun()
    with col_m2:
        if st.button(
            "🌐 Đấu Online (2 Máy khác nhau)",
            use_container_width=True,
            type="primary" if st.session_state.game_mode == "online_pvp" else "secondary",
        ):
            st.session_state.game_mode = "online_pvp"
            # Reset board local, sẽ lấy từ phòng sau
            st.session_state.board = []
            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            # Không reset room_id, giữ nguyên
            st.rerun()

    # Chọn kích thước bàn cờ (chỉ có hiệu lực cho AI và tạo phòng mới)
    if st.session_state.game_mode == "vs_ai":
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            if st.button("📐 Bàn cờ 3x3 (Nối 3)", use_container_width=True):
                st.session_state.size = 3
                st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.rerun()
        with col_s2:
            if st.button("📐 Bàn cờ 10x10 (Nối 5)", use_container_width=True):
                st.session_state.size = 10
                st.session_state.board = [[" " for _ in range(10)] for _ in range(10)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.rerun()
        with col_s3:
            if st.button("📐 Bàn cờ 12x12 (Nối 5)", use_container_width=True):
                st.session_state.size = 12
                st.session_state.board = [[" " for _ in range(12)] for _ in range(12)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
                st.rerun()
        size = st.session_state.size
    else:
        # Online: kích thước lấy từ phòng hoặc mặc định
        size = st.session_state.size  # sẽ cập nhật sau

    # ----------------- XỬ LÝ ONLINE PVP -----------------
    if st.session_state.game_mode == "online_pvp":
        st.markdown("---")
        st.markdown("### 🌐 Kết nối 2 máy khác nhau")
        st.info(
            "💡 **Cách chơi 2 máy:** Đặt tên phòng tùy ý hoặc dùng mặc định, sau đó bấm **Tạo phòng** hoặc **Tham gia phòng** và copy đường dẫn trình duyệt gửi cho bạn bè mở trên máy của họ."
        )

        col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
        with col_r1:
            entered_room = st.text_input("Mã phòng chơi", value=st.session_state.room_id)
        with col_r2:
            if st.button("Tạo phòng mới", use_container_width=True):
                # Tạo phòng mới với kích thước hiện tại
                new_room = entered_room if entered_room.strip() else generate_room_id()
                if new_room in shared_rooms:
                    st.warning("Phòng đã tồn tại, hãy tham gia hoặc đổi mã khác.")
                else:
                    # Rời phòng cũ
                    if st.session_state.room_id and st.session_state.my_symbol:
                        leave_room(st.session_state.room_id, user)
                    # Tạo phòng mới
                    init_room(new_room, st.session_state.size)
                    symbol = join_room(new_room, user)
                    if symbol:
                        st.session_state.room_id = new_room
                        st.session_state.my_symbol = symbol
                        st.session_state.is_room_creator = True
                        st.query_params["room"] = new_room
                        st.success(f"Đã tạo phòng: {new_room} - Bạn là {symbol}")
                        st.rerun()
        with col_r3:
            if st.button("Tham gia phòng", use_container_width=True):
                room_id = entered_room.strip()
                if not room_id:
                    st.warning("Vui lòng nhập mã phòng.")
                elif room_id not in shared_rooms:
                    st.warning("Phòng không tồn tại. Hãy tạo phòng mới.")
                else:
                    # Rời phòng cũ
                    if st.session_state.room_id and st.session_state.my_symbol:
                        leave_room(st.session_state.room_id, user)
                    symbol = join_room(room_id, user)
                    if symbol is None:
                        st.warning("Phòng đã đầy hoặc không thể tham gia.")
                    else:
                        st.session_state.room_id = room_id
                        st.session_state.my_symbol = symbol
                        st.session_state.is_room_creator = False
                        st.query_params["room"] = room_id
                        st.success(f"Đã tham gia phòng: {room_id} - Bạn là {symbol}")
                        st.rerun()

        st.markdown(f"🔗 **Mã phòng hiện tại:** `{st.session_state.room_id}` (Bạn là {st.session_state.my_symbol})")

        # Lấy trạng thái phòng từ shared
        room_id = st.session_state.room_id
        if room_id in shared_rooms:
            room = shared_rooms[room_id]
            board = room["board"]
            size = room["size"]
            turn = room["turn"]
            winner = room["winner"]
            winning_line = room.get("winning_line", [])
            players = room["players"]
            # Cập nhật kích thước cho session_state để CSS
            st.session_state.size = size
            # Đồng bộ lên board local để hiển thị
            st.session_state.board = board
            st.session_state.turn = turn
            st.session_state.winner = winner
            st.session_state.winning_line = winning_line
        else:
            st.warning("Phòng chưa được tạo. Hãy tạo phòng hoặc tham gia phòng hợp lệ.")
            board = None
            size = st.session_state.size
            turn = "X"
            winner = None
            winning_line = []
            players = {}
            # Nếu chưa có phòng, không cho đánh
    else:
        # Chế độ AI: sử dụng board local
        board = st.session_state.board
        size = st.session_state.size
        turn = st.session_state.turn
        winner = st.session_state.winner
        winning_line = st.session_state.winning_line
        players = {user: "X"}  # chỉ để hiển thị

    # ----------------- HIỂN THỊ TRẠNG THÁI -----------------
    mode_text = "Đấu với Máy (AI)" if st.session_state.game_mode == "vs_ai" else "Đấu Online (2 Máy)"
    if not winner:
        if st.session_state.game_mode == "vs_ai":
            turn_msg = f"Lượt đi: <b>{'Bạn (X)' if turn == 'X' else 'Máy (O)'}</b>"
        else:
            # Online
            if turn == st.session_state.my_symbol:
                turn_msg = f"Lượt đi: <b>Bạn ({turn})</b>"
            else:
                turn_msg = f"Lượt đi: <b>Đối thủ ({turn})</b>"
    else:
        turn_msg = "Trận đấu đã kết thúc!"

    st.markdown(
        f"<div class='status-card'>🎮 Chế độ: <b>{mode_text}</b> (Phòng: <code>{st.session_state.room_id}</code>) | {turn_msg}</div>",
        unsafe_allow_html=True,
    )

    # ----------------- HIỂN THỊ BÀN CỜ -----------------
    if board is not None:
        st.markdown('<div class="chess-board-wrapper">', unsafe_allow_html=True)
        for r in range(size):
            cols = st.columns(size)
            for c in range(size):
                val = board[r][c]
                label = val if val != " " else ""
                is_winning_cell = (r, c) in winning_line

                # Xác định xem ô có thể click không
                disabled = False
                if st.session_state.game_mode == "online_pvp":
                    # Nếu không có người chơi hoặc không phải lượt của mình hoặc đã có người thắng
                    if not players or winner is not None:
                        disabled = True
                    elif st.session_state.my_symbol not in players.values():
                        disabled = True
                    elif turn != st.session_state.my_symbol:
                        disabled = True
                    elif val != " ":
                        disabled = True
                else:
                    # AI mode: chỉ cho phép click khi là X và chưa có người thắng và chưa kết thúc
                    if winner is not None or val != " " or turn != "X":
                        disabled = True

                if is_winning_cell:
                    with cols[c]:
                        st.markdown(f'<div class="win-cell"><button>{label}</button></div>', unsafe_allow_html=True)
                else:
                    # Tạo button
                    if cols[c].button(label, key=f"btn_{r}_{c}_{st.session_state.game_mode}", disabled=disabled):
                        if st.session_state.game_mode == "vs_ai":
                            # Nước đi của người
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
                            elif is_full(st.session_state.board, size):
                                st.session_state.winner = "Draw"
                            else:
                                st.session_state.turn = "O"
                                # AI đi
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
                                elif is_full(st.session_state.board, size):
                                    st.session_state.winner = "Draw"
                                else:
                                    st.session_state.turn = "X"
                            st.rerun()
                        else:
                            # Online PVP: áp dụng nước đi qua shared_rooms
                            success, msg = apply_move(room_id, r, c, user)
                            if success:
                                st.rerun()
                            else:
                                st.warning(msg)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Chưa có bàn cờ. Hãy tạo hoặc tham gia phòng.")

    # ----------------- THÔNG BÁO KẾT QUẢ -----------------
    if winner:
        if winner == "X":
            st.success("🎉 Người chơi X chiến thắng! Đường kẻ được tô sáng.")
        elif winner == "O":
            st.success("🎉 Người chơi O chiến thắng! Đường kẻ được tô sáng.")
        elif winner == "Draw":
            st.warning("🤝 Trận đấu hòa!")

    # ----------------- NÚT CHƠI LẠI -----------------
    r_col1, r_col2, r_col3 = st.columns([2, 1, 2])
    with r_col2:
        if st.button("🔄 Chơi Ván Mới", use_container_width=True, type="primary"):
            if st.session_state.game_mode == "vs_ai":
                st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
                st.session_state.turn = "X"
                st.session_state.winner = None
                st.session_state.winning_line = []
            else:
                # Online: reset phòng (giữ nguyên người chơi)
                room_id = st.session_state.room_id
                if room_id in shared_rooms:
                    room = shared_rooms[room_id]
                    room["board"] = [[" " for _ in range(size)] for _ in range(size)]
                    room["turn"] = "X"
                    room["winner"] = None
                    room["winning_line"] = []
                    # Giữ nguyên players
            st.rerun()
