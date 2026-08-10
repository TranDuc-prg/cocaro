import random
import streamlit as st
import hashlib
import json
import os
from streamlit_autorefresh import st_autorefresh

# ============================================================
# CẤU HÌNH
# ============================================================

st.set_page_config(
    page_title="Cờ Caro Trực Tuyến",
    page_icon="🪵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

ROOMS_FILE = "rooms.json"


# ============================================================
# QUẢN LÝ PHÒNG
# ============================================================

def read_rooms():
    if os.path.exists(ROOMS_FILE):
        try:
            with open(ROOMS_FILE, "r", encoding="utf-8") as f:
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


# ============================================================
# KIỂM TRA THẮNG
# ============================================================

def check_winner(board, size):

    win_len = 3 if size == 3 else 5

    # Hàng ngang
    for r in range(size):
        for c in range(size - win_len + 1):

            symbol = board[r][c]

            if symbol != " " and all(
                board[r][c + k] == symbol
                for k in range(win_len)
            ):
                return symbol, [
                    (r, c + k)
                    for k in range(win_len)
                ]

    # Hàng dọc
    for c in range(size):
        for r in range(size - win_len + 1):

            symbol = board[r][c]

            if symbol != " " and all(
                board[r + k][c] == symbol
                for k in range(win_len)
            ):
                return symbol, [
                    (r + k, c)
                    for k in range(win_len)
                ]

    # Chéo xuống phải
    for r in range(size - win_len + 1):
        for c in range(size - win_len + 1):

            symbol = board[r][c]

            if symbol != " " and all(
                board[r + k][c + k] == symbol
                for k in range(win_len)
            ):
                return symbol, [
                    (r + k, c + k)
                    for k in range(win_len)
                ]

    # Chéo xuống trái
    for r in range(size - win_len + 1):
        for c in range(win_len - 1, size):

            symbol = board[r][c]

            if symbol != " " and all(
                board[r + k][c - k] == symbol
                for k in range(win_len)
            ):
                return symbol, [
                    (r + k, c - k)
                    for k in range(win_len)
                ]

    return None, []


def is_full(board, size):
    return all(
        board[r][c] != " "
        for r in range(size)
        for c in range(size)
    )


# ============================================================
# AI
# ============================================================

def ai_move(size, board):

    empty_cells = []

    for r in range(size):
        for c in range(size):

            if board[r][c] == " ":

                has_neighbor = any(
                    0 <= r + dr < size
                    and
                    0 <= c + dc < size
                    and
                    board[r + dr][c + dc] != " "
                    for dr in [-1, 0, 1]
                    for dc in [-1, 0, 1]
                    if not (dr == 0 and dc == 0)
                )

                if has_neighbor or size == 3:
                    empty_cells.append((r, c))

    if empty_cells:
        return random.choice(empty_cells)

    return size // 2, size // 2


# ============================================================
# ELO ONLINE
# ============================================================

def update_elo_online(room_id, winner):

    room = get_room(room_id)

    if not room:
        return

    players = room["players"]

    if len(players) != 2:
        return

    user_list = list(players.keys())

    p1 = user_list[0]
    p2 = user_list[1]

    s1 = players[p1]
    s2 = players[p2]

    score_changes = {}

    if winner == "X":

        win_user = p1 if s1 == "X" else p2
        lose_user = p2 if s1 == "X" else p1

        st.session_state.users[win_user] = (
            st.session_state.users.get(win_user, 1000) + 15
        )

        st.session_state.users[lose_user] = max(
            100,
            st.session_state.users.get(lose_user, 1000) - 10
        )

        score_changes[win_user] = "+15"
        score_changes[lose_user] = "-10"

        for u in [win_user, lose_user]:

            st.session_state.match_history.append({
                "player": u,
                "opponent": (
                    lose_user
                    if u == win_user
                    else win_user
                ),
                "result": (
                    "Thắng"
                    if u == win_user
                    else "Thua"
                ),
                "score": (
                    "+15"
                    if u == win_user
                    else "-10"
                ),
            })

    elif winner == "O":

        win_user = p1 if s1 == "O" else p2
        lose_user = p2 if s1 == "O" else p1

        st.session_state.users[win_user] = (
            st.session_state.users.get(win_user, 1000) + 15
        )

        st.session_state.users[lose_user] = max(
            100,
            st.session_state.users.get(lose_user, 1000) - 10
        )

        score_changes[win_user] = "+15"
        score_changes[lose_user] = "-10"

        for u in [win_user, lose_user]:

            st.session_state.match_history.append({
                "player": u,
                "opponent": (
                    lose_user
                    if u == win_user
                    else win_user
                ),
                "result": (
                    "Thắng"
                    if u == win_user
                    else "Thua"
                ),
                "score": (
                    "+15"
                    if u == win_user
                    else "-10"
                ),
            })

    elif winner == "Draw":

        for u in [p1, p2]:

            score_changes[u] = "0"

            st.session_state.match_history.append({
                "player": u,
                "opponent": (
                    p2
                    if u == p1
                    else p1
                ),
                "result": "Hòa",
                "score": "0",
            })

    room["last_score"] = score_changes

    save_room(room_id, room)


# ============================================================
# NƯỚC ĐI ONLINE
# ============================================================

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

        save_room(room_id, room)

        update_elo_online(room_id, winner)

        room = get_room(room_id)

    elif is_full(board, size):

        room["winner"] = "Draw"
        room["game_ended"] = True

        save_room(room_id, room)

        update_elo_online(room_id, "Draw")

    else:

        room["turn"] = (
            "O"
            if symbol == "X"
            else "X"
        )

        save_room(room_id, room)

    return True, "Thành công"


# ============================================================
# TẠO ROOM ID
# ============================================================

def generate_room_id():

    return (
        "phong_"
        +
        hashlib.md5(
            str(random.random()).encode()
        ).hexdigest()[:8]
    )


# ============================================================
# SESSION STATE
# ============================================================

if "users" not in st.session_state:
    st.session_state.users = {}

if "match_history" not in st.session_state:
    st.session_state.match_history = []

if "current_user" not in st.session_state:
    st.session_state.current_user = ""

if "size" not in st.session_state:
    st.session_state.size = 10

if "board" not in st.session_state:
    st.session_state.board = [
        [" " for _ in range(10)]
        for _ in range(10)
    ]

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

current_size = st.session_state.size

# ============================================================
# CSS GIAO DIỆN - TỐI ƯU ĐIỆN THOẠI + MÁY TÍNH
# ============================================================

css_code = f"""
<style>

.stApp {{
    background: #fcf8ee !important;
}}

.block-container {{
    width: 100% !important;
    max-width: 980px !important;
    padding: 14px 10px 40px !important;
    margin: 0 auto !important;
}}

.main-title {{
    text-align: center;
    color: #4b2e1f;
    font-size: clamp(28px, 5vw, 44px);
    font-weight: 800;
    margin: 8px 0 18px;
}}

.custom-card {{
    background: #fff;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,.08);
    border: 1px solid #eadfce;
}}

.status-card {{
    width: 100%;
    box-sizing: border-box;
    background: #fffaf0;
    border-left: 6px solid #8b4513;
    padding: 12px 10px;
    border-radius: 12px;
    margin: 12px 0 18px;
    text-align: center;
    font-size: 16px;
    color: #5c4033;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}}

/* ============================================================
   BÀN CỜ: QUAN TRỌNG - DÙNG CONTAINER CÓ KEY
   Không dùng :has() và không dùng div HTML bao quanh st.columns.
   ============================================================ */

.st-key-caro-board {{
    width: min(94vw, 700px) !important;
    max-width: 700px !important;
    margin: 12px auto 18px !important;
    padding: 5px !important;
    box-sizing: border-box !important;
    background: #b98243 !important;
    border: 5px solid #6e3d14 !important;
    border-radius: 12px !important;
    box-shadow: 0 7px 20px rgba(72,40,12,.28) !important;
}}

/* Mỗi st.columns(size) là một HÀNG của bàn cờ */
.st-key-caro-board [data-testid="stHorizontalBlock"] {{
    display: grid !important;
    grid-template-columns: repeat({current_size}, minmax(0, 1fr)) !important;
    grid-auto-flow: row !important;
    gap: 0 !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    align-items: stretch !important;
}}

.st-key-caro-board [data-testid="column"] {{
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
    flex: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}

.st-key-caro-board [data-testid="column"] > div {{
    width: 100% !important;
    min-width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}}

/* Ô Caro là hình vuông */
.st-key-caro-board div.stButton {{
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}}

.st-key-caro-board div.stButton > button {{
    width: 100% !important;
    height: auto !important;
    aspect-ratio: 1 / 1 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 0 !important;
    border: 1px solid #9a672f !important;
    background: #f5dfb4 !important;
    color: #171717 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: clamp(15px, {max(3.0, 100/current_size)}vw, 34px) !important;
    font-weight: 900 !important;
    line-height: 1 !important;
    box-shadow: none !important;
    transition: background .12s ease, transform .08s ease !important;
    touch-action: manipulation !important;
    -webkit-tap-highlight-color: transparent !important;
}}

.st-key-caro-board div.stButton > button:hover {{
    background: #e8cc91 !important;
    border-color: #75451e !important;
}}

.st-key-caro-board div.stButton > button:active {{
    transform: scale(.96) !important;
}}

.st-key-caro-board div.stButton > button:disabled {{
    opacity: 1 !important;
    color: #171717 !important;
    background: #f5dfb4 !important;
}}

.st-key-caro-board div.stButton > button p {{
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    font-size: inherit !important;
    font-weight: 900 !important;
}}

/* Ô nằm trên đường thắng */
.caro-win-cell {{
    width: 100%;
    aspect-ratio: 1 / 1;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #4ade80;
    border: 2px solid #15803d;
    animation: caroWin 1s ease-in-out infinite;
}}

.caro-win-cell span {{
    font-size: clamp(15px, {max(3.0, 100/current_size)}vw, 34px);
    font-weight: 900;
    line-height: 1;
}}

@keyframes caroWin {{
    0%, 100% {{
        background: #4ade80;
        box-shadow: inset 0 0 0 rgba(22,163,74,0);
    }}
    50% {{
        background: #86efac;
        box-shadow: inset 0 0 12px rgba(22,163,74,.35);
    }}
}}

/* Các hàng Streamlit không được tạo khoảng cách */
.st-key-caro-board > div {{
    gap: 0 !important;
}}

/* ============================================================
   MOBILE
   ============================================================ */

@media (max-width: 600px) {{
    .block-container {{
        width: 100% !important;
        max-width: 100% !important;
        padding: 8px 4px 30px !important;
    }}

    .main-title {{
        font-size: 28px !important;
        line-height: 1.2 !important;
        margin: 6px 0 12px !important;
    }}

    .status-card {{
        font-size: 14px !important;
        padding: 10px 6px !important;
        margin: 8px 0 12px !important;
    }}

    .st-key-caro-board {{
        width: calc(100vw - 10px) !important;
        max-width: calc(100vw - 10px) !important;
        margin: 8px auto 16px !important;
        padding: 3px !important;
        border-width: 3px !important;
        border-radius: 8px !important;
    }}

    .st-key-caro-board [data-testid="stHorizontalBlock"] {{
        grid-template-columns: repeat({current_size}, minmax(0, 1fr)) !important;
        gap: 0 !important;
    }}

    .st-key-caro-board [data-testid="column"] {{
        padding: 0 !important;
        margin: 0 !important;
    }}

    .st-key-caro-board div.stButton > button {{
        aspect-ratio: 1 / 1 !important;
        min-height: 0 !important;
        height: auto !important;
        border-width: 1px !important;
        font-size: {11 if current_size >= 12 else 15}px !important;
    }}

    .caro-win-cell span {{
        font-size: {11 if current_size >= 12 else 15}px !important;
    }}
}}

@media (max-width: 390px) {{
    .st-key-caro-board {{
        width: calc(100vw - 6px) !important;
        max-width: calc(100vw - 6px) !important;
        padding: 2px !important;
        border-width: 2px !important;
    }}

    .st-key-caro-board div.stButton > button {{
        font-size: {9 if current_size >= 12 else 13}px !important;
    }}

    .caro-win-cell span {{
        font-size: {9 if current_size >= 12 else 13}px !important;
    }}
}}

</style>
"""

st.markdown(css_code, unsafe_allow_html=True)

# ============================================================
# ĐĂNG NHẬP
# ============================================================

if not st.session_state.current_user:

    st.markdown(
        """
        <div class="main-title">
            🪵 Cờ Caro Gỗ Trực Tuyến 🪵
        </div>
        """,
        unsafe_allow_html=True
    )

    _, col_login, _ = st.columns(
        [1, 2, 1]
    )

    with col_login:

        st.markdown(
            """
            <div class="custom-card">
                <h3>👤 Đăng nhập</h3>
                <p>
                    Nhập tên của bạn để bắt đầu chơi.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        username_input = st.text_input(
            "Tên hiển thị",
            placeholder="Nhập tên..."
        )

        if st.button(
            "🎮 Vào Trò Chơi",
            use_container_width=True,
            type="primary"
        ):

            if username_input.strip():

                name = username_input.strip()

                st.session_state.current_user = name

                if name not in st.session_state.users:

                    st.session_state.users[name] = 1000

                st.rerun()

            else:

                st.warning(
                    "Vui lòng nhập tên hợp lệ!"
                )

    st.stop()


# ============================================================
# USER
# ============================================================

user = st.session_state.current_user

user_score = st.session_state.users.get(
    user,
    1000
)


# ============================================================
# HEADER
# ============================================================

col_h1, col_h2 = st.columns(
    [3, 1]
)

with col_h1:

    st.markdown(
        f"""
        🎮 Người chơi:
        **{user}**
        &nbsp; | &nbsp;
        ⭐ Elo:
        **{user_score}**
        """
    )


with col_h2:

    if st.button(
        "Đổi người chơi",
        use_container_width=True
    ):

        if (
            st.session_state.game_mode
            == "online_pvp"
            and st.session_state.room_id
        ):

            leave_room(
                st.session_state.room_id,
                user
            )

        st.session_state.current_user = ""

        st.rerun()


st.markdown(
    """
    <div class="main-title">
        🪵 Cờ Caro Gỗ Trực Tuyến 🪵
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# QUERY PARAMS
# ============================================================

query_params = st.query_params

room_from_url = query_params.get(
    "room",
    None
)

if room_from_url:

    st.session_state.room_id = room_from_url


# ============================================================
# TAB
# ============================================================

tab1, tab2 = st.tabs(
    [
        "🎮 Vào Trận Đấu",
        "🏆 Bảng Xếp Hạng & Lịch Sử"
    ]
)


# ============================================================
# BẢNG XẾP HẠNG
# ============================================================

with tab2:

    col_tb1, col_tb2 = st.columns(2)

    with col_tb1:

        st.markdown(
            "### 🏆 Top Elo"
        )

        if not st.session_state.users:

            st.info(
                "Chưa có người chơi."
            )

        else:

            sorted_users = sorted(
                st.session_state.users.items(),
                key=lambda x: x[1],
                reverse=True
            )

            for idx, (u_name, u_pts) in enumerate(
                sorted_users[:5],
                1
            ):

                medal = (
                    "🥇"
                    if idx == 1
                    else
                    (
                        "🥈"
                        if idx == 2
                        else
                        (
                            "🥉"
                            if idx == 3
                            else f"{idx}."
                        )
                    )
                )

                st.markdown(
                    f"{medal} **{u_name}** — `{u_pts} pts`"
                )

            with st.expander(
                "Xem tất cả người chơi"
            ):

                for idx, (u_name, u_pts) in enumerate(
                    sorted_users,
                    1
                ):

                    st.markdown(
                        f"{idx}. **{u_name}** — `{u_pts} pts`"
                    )


    with col_tb2:

        st.markdown(
            "### 📜 Lịch sử gần đây"
        )

        if not st.session_state.match_history:

            st.info(
                "Chưa có trận nào."
            )

        else:

            for match in st.session_state.match_history[-10:]:

                color_res = (
                    "green"
                    if match["result"] == "Thắng"
                    else
                    (
                        "red"
                        if match["result"] == "Thua"
                        else "orange"
                    )
                )

                st.markdown(
                    f"""
                    - {match['player']}
                    vs {match['opponent']}:
                    <span style="
                        color:{color_res};
                        font-weight:bold;
                    ">
                        {match['result']}
                    </span>
                    (`{match['score']}`)
                    """,
                    unsafe_allow_html=True
                )


# ============================================================
# GAME
# ============================================================

with tab1:

    # --------------------------------------------------------
    # CHỌN CHẾ ĐỘ
    # --------------------------------------------------------

    col_m1, col_m2 = st.columns(2)

    with col_m1:

        if st.button(
            "🤖 Đấu với Máy (AI)",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.game_mode == "vs_ai"
                else "secondary"
            )
        ):

            if (
                st.session_state.game_mode
                == "online_pvp"
                and st.session_state.room_id
            ):

                leave_room(
                    st.session_state.room_id,
                    user
                )

            st.session_state.game_mode = "vs_ai"

            size = st.session_state.size

            st.session_state.board = [
                [" " for _ in range(size)]
                for _ in range(size)
            ]

            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.win_score = None

            st.rerun()


    with col_m2:

        if st.button(
            "🌐 Đấu Online (2 Máy)",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.game_mode == "online_pvp"
                else "secondary"
            )
        ):

            st.session_state.game_mode = "online_pvp"

            st.session_state.board = []

            st.session_state.turn = "X"

            st.session_state.winner = None

            st.session_state.winning_line = []

            st.session_state.win_score = None

            st.rerun()


    # --------------------------------------------------------
    # KÍCH THƯỚC BÀN
    # --------------------------------------------------------

    if st.session_state.game_mode == "vs_ai":

        st.markdown(
            "### 📐 Kích thước bàn cờ"
        )

        col_s1, col_s2, col_s3 = st.columns(3)

        sizes = [
            (col_s1, 3),
            (col_s2, 10),
            (col_s3, 12)
        ]

        for col, board_size in sizes:

            with col:

                if st.button(
                    f"📐 {board_size}x{board_size}",
                    use_container_width=True
                ):

                    st.session_state.size = board_size

                    st.session_state.board = [
                        [
                            " "
                            for _ in range(board_size)
                        ]
                        for _ in range(board_size)
                    ]

                    st.session_state.turn = "X"

                    st.session_state.winner = None

                    st.session_state.winning_line = []

                    st.session_state.win_score = None

                    st.rerun()


    # ========================================================
    # ONLINE
    # ========================================================

    if st.session_state.game_mode == "online_pvp":

        st_autorefresh(
            interval=2000,
            key="auto_refresh"
        )

        st.markdown("---")

        st.markdown(
            "### 🌐 Kết nối 2 máy"
        )

        st.info(
            "Tạo hoặc tham gia phòng rồi gửi mã phòng "
            "cho người chơi thứ 2."
        )

        col_r1, col_r2, col_r3 = st.columns(
            [2, 1, 1]
        )

        with col_r1:

            entered_room = st.text_input(
                "Mã phòng",
                value=st.session_state.room_id
            )

        with col_r2:

            if st.button(
                "Tạo phòng",
                use_container_width=True
            ):

                new_room = (
                    entered_room.strip()
                    if entered_room.strip()
                    else generate_room_id()
                )

                if get_room(new_room):

                    st.warning(
                        "Phòng đã tồn tại."
                    )

                else:

                    init_room(
                        new_room,
                        st.session_state.size
                    )

                    symbol = join_room(
                        new_room,
                        user
                    )

                    if symbol:

                        st.session_state.room_id = new_room

                        st.session_state.my_symbol = symbol

                        st.session_state.is_room_creator = True

                        st.query_params["room"] = new_room

                        st.success(
                            f"Đã tạo phòng {new_room}. "
                            f"Bạn là {symbol}."
                        )

                        st.rerun()


        with col_r3:

            if st.button(
                "Tham gia",
                use_container_width=True
            ):

                room_id = entered_room.strip()

                if not room_id:

                    st.warning(
                        "Nhập mã phòng."
                    )

                elif not get_room(room_id):

                    st.warning(
                        "Phòng không tồn tại."
                    )

                else:

                    symbol = join_room(
                        room_id,
                        user
                    )

                    if symbol is None:

                        st.warning(
                            "Phòng đã đầy."
                        )

                    else:

                        st.session_state.room_id = room_id

                        st.session_state.my_symbol = symbol

                        st.session_state.is_room_creator = False

                        st.query_params["room"] = room_id

                        st.success(
                            f"Bạn là {symbol}."
                        )

                        st.rerun()


        st.markdown(
            f"""
            🔗 **Phòng:**
            `{st.session_state.room_id}`
            &nbsp; | &nbsp;
            **Bạn:**
            `{st.session_state.my_symbol}`
            """
        )


        # ----------------------------------------------------
        # LẤY ROOM
        # ----------------------------------------------------

        room_data = get_room(
            st.session_state.room_id
        )

        if room_data:

            board = room_data["board"]

            size = room_data["size"]

            turn = room_data["turn"]

            winner = room_data["winner"]

            winning_line = room_data.get(
                "winning_line",
                []
            )

            players = room_data["players"]

            last_score = room_data.get(
                "last_score",
                None
            )

            game_ended = room_data.get(
                "game_ended",
                False
            )

            st.session_state.size = size

            st.session_state.board = board

            st.session_state.turn = turn

            st.session_state.winner = winner

            st.session_state.winning_line = winning_line

            if game_ended and last_score and winner:

                st.session_state.win_score = last_score

                if user in last_score:

                    score = last_score[user]

                    if score == "+15":

                        st.balloons()

                        st.success(
                            "🎉 Bạn đã thắng! +15 điểm"
                        )

                    elif score == "-10":

                        st.error(
                            "😢 Bạn đã thua! -10 điểm"
                        )

                    elif score == "0":

                        st.info(
                            "🤝 Hòa! 0 điểm"
                        )

        else:

            board = None

            size = st.session_state.size

            turn = "X"

            winner = None

            winning_line = []

            players = {}


    # ========================================================
    # AI MODE
    # ========================================================

    else:

        board = st.session_state.board

        size = st.session_state.size

        turn = st.session_state.turn

        winner = st.session_state.winner

        winning_line = st.session_state.winning_line

        players = {
            user: "X"
        }


    # ========================================================
    # TRẠNG THÁI
    # ========================================================

    mode_text = (
        "Đấu với Máy 🤖"
        if st.session_state.game_mode == "vs_ai"
        else "Đấu Online 🌐"
    )

    if not winner:

        if st.session_state.game_mode == "vs_ai":

            turn_msg = (
                "Lượt đi: "
                "<b>"
                +
                (
                    "Bạn (X)"
                    if turn == "X"
                    else "Máy (O)"
                )
                +
                "</b>"
            )

        else:

            turn_msg = (
                "Lượt đi: "
                "<b>"
                +
                (
                    f"Bạn ({turn})"
                    if turn == st.session_state.my_symbol
                    else f"Đối thủ ({turn})"
                )
                +
                "</b>"
            )

    else:

        turn_msg = (
            "🏁 Trận đấu đã kết thúc!"
        )


    st.markdown(
        f"""
        <div class="status-card">
            🎮 {mode_text}
            &nbsp; | &nbsp;
            {turn_msg}
        </div>
        """,
        unsafe_allow_html=True
    )


 # ============================================================
# BÀN CỜ CARO - RESPONSIVE MOBILE / DESKTOP
# ============================================================

if board is not None:

    # Container có key để CSS chỉ tác động vào bàn cờ.
    # Đây là điểm quan trọng: HTML <div> của st.markdown không thể
    # bao trực tiếp các widget Streamlit phía sau nó.
    with st.container(key="caro-board"):

        for r in range(size):

            # 1 hàng của bàn cờ = 1 st.columns(size)
            cols = st.columns(size, gap=None)

            for c in range(size):

                val = board[r][c]
                is_winning_cell = (r, c) in winning_line

                # Hiển thị quân theo kiểu Caro chuẩn X / O
                if val == "X":
                    label = "X"
                elif val == "O":
                    label = "O"
                else:
                    label = ""

                # ----------------------------------------------
                # XÁC ĐỊNH Ô CÓ ĐƯỢC ĐÁNH HAY KHÔNG
                # ----------------------------------------------

                disabled = False

                if st.session_state.game_mode == "online_pvp":

                    if not players:
                        disabled = True

                    elif winner is not None:
                        disabled = True

                    elif st.session_state.my_symbol not in players.values():
                        disabled = True

                    elif turn != st.session_state.my_symbol:
                        disabled = True

                    elif val != " ":
                        disabled = True

                else:

                    if winner is not None:
                        disabled = True

                    elif val != " ":
                        disabled = True

                    elif turn != "X":
                        disabled = True

                # ----------------------------------------------
                # Ô THUỘC DÒNG THẮNG
                # ----------------------------------------------

                if is_winning_cell:

                    with cols[c]:
                        st.markdown(
                            f"""<div class="caro-win-cell"><span>{label}</span></div>""",
                            unsafe_allow_html=True
                        )

                    continue

                # ----------------------------------------------
                # Ô BÌNH THƯỜNG
                # ----------------------------------------------

                with cols[c]:
                    clicked = st.button(
                        label,
                        key=(
                            f"caro_cell_"
                            f"{st.session_state.game_mode}_"
                            f"{size}_"
                            f"{r}_{c}"
                        ),
                        disabled=disabled,
                        use_container_width=True
                    )

                if not clicked:
                    continue

                # ==================================================
                # CHẾ ĐỘ ĐẤU VỚI AI
                # ==================================================

                if st.session_state.game_mode == "vs_ai":

                    st.session_state.board[r][c] = "X"

                    w, line = check_winner(
                        st.session_state.board,
                        size
                    )

                    # Người chơi X thắng
                    if w:

                        st.session_state.winner = w
                        st.session_state.winning_line = line

                        if w == "X":
                            st.session_state.users[user] = (
                                st.session_state.users.get(user, 1000) + 15
                            )

                            st.session_state.match_history.append({
                                "player": user,
                                "opponent": "AI Robot",
                                "result": "Thắng",
                                "score": "+15"
                            })

                            st.session_state.win_score = {user: "+15"}

                    # Bàn đầy
                    elif is_full(st.session_state.board, size):

                        st.session_state.winner = "Draw"
                        st.session_state.win_score = {user: "0"}

                    # AI thực hiện lượt đi
                    else:

                        st.session_state.turn = "O"

                        ai_r, ai_c = ai_move(
                            size,
                            st.session_state.board
                        )

                        st.session_state.board[ai_r][ai_c] = "O"

                        w2, line2 = check_winner(
                            st.session_state.board,
                            size
                        )

                        # AI thắng
                        if w2:

                            st.session_state.winner = w2
                            st.session_state.winning_line = line2

                            if w2 == "O":

                                st.session_state.users[user] = max(
                                    100,
                                    st.session_state.users.get(user, 1000) - 10
                                )

                                st.session_state.match_history.append({
                                    "player": user,
                                    "opponent": "AI Robot",
                                    "result": "Thua",
                                    "score": "-10"
                                })

                                st.session_state.win_score = {user: "-10"}

                        # Hòa sau lượt AI
                        elif is_full(
                            st.session_state.board,
                            size
                        ):

                            st.session_state.winner = "Draw"
                            st.session_state.win_score = {user: "0"}

                        else:
                            st.session_state.turn = "X"

                    st.rerun()

                # ==================================================
                # CHẾ ĐỘ ONLINE 2 NGƯỜI
                # ==================================================

                else:

                    success, msg = apply_move(
                        st.session_state.room_id,
                        r,
                        c,
                        user
                    )

                    if success:
                        st.rerun()
                    else:
                        st.warning(msg)

else:

    st.info(
        "Chưa có bàn cờ. Hãy tạo hoặc tham gia phòng."
    )


# ============================================================
# THÔNG BÁO KẾT QUẢ
# ============================================================

if winner:

    if winner == "X":
        st.success("🎉 Người chơi X chiến thắng!")

    elif winner == "O":
        st.success("🎉 Người chơi O chiến thắng!")

    elif winner == "Draw":
        st.warning("🤝 Trận đấu hòa!")


# ============================================================
# CHƠI VÁN MỚI
# ============================================================

st.markdown("---")

_, restart_col, _ = st.columns([1, 2, 1])

with restart_col:

    if st.button(
        "🔄 Chơi Ván Mới",
        use_container_width=True,
        type="primary"
    ):

        if st.session_state.game_mode == "vs_ai":

            st.session_state.board = [
                [" " for _ in range(size)]
                for _ in range(size)
            ]

            st.session_state.turn = "X"
            st.session_state.winner = None
            st.session_state.winning_line = []
            st.session_state.win_score = None

        else:

            room_id = st.session_state.room_id
            room = get_room(room_id)

            if room:

                room["board"] = [
                    [" " for _ in range(size)]
                    for _ in range(size)
                ]

                room["turn"] = "X"
                room["winner"] = None
                room["winning_line"] = []
                room["last_score"] = None
                room["game_ended"] = False

                save_room(room_id, room)

                st.session_state.win_score = None

        st.rerun()
