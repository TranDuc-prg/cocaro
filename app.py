import random
import streamlit as st

st.set_page_config(
    page_title="Cờ Caro Gỗ Trực Tuyến", page_icon="🪵", layout="centered"
)

# Khởi tạo session state (Không còn tài khoản mặc định sẵn)
if "users" not in st.session_state:
  st.session_state.users = {}

if "match_history" not in st.session_state:
  st.session_state.match_history = []

if "current_user" not in st.session_state:
  st.session_state.current_user = ""

if "board" not in st.session_state:
  st.session_state.size = 10
  st.session_state.board = [
      [" " for _ in range(10)] for _ in range(10)
  ]
  st.session_state.turn = "X"
  st.session_state.winner = None
  st.session_state.winning_line = []
  st.session_state.game_mode = "vs_ai"
  st.session_state.room_id = "phong_mac_dinh"

current_size = st.session_state.size

# Giao diện CSS hiện đại, ấm áp phong cách gỗ, có hiệu ứng đường kẻ thắng nhấp nháy
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

/* Khung bọc bàn cờ gỗ */
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

/* Nút ô cờ thông thường */
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

/* Hiệu ứng các ô đạt chuỗi thắng (đường kẻ ngang/dọc/chéo) */
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

# ----------------- MÀN HÌNH NHẬP TÊN NGƯỜI DÙNG -----------------
if not st.session_state.current_user:
  st.markdown(
      "<h2 style='text-align: center; color: #5c4033;'>🪵 Cờ Caro Gỗ Trực"
      " Tuyến 🪵</h2>",
      unsafe_allow_html=True,
  )
  _, col_login, _ = st.columns([1, 2, 1])
  with col_login:
    st.markdown(
        "<div"
        " class='custom-card'><h3>👤 Đăng nhập người"
        " chơi</h3><p>Vui lòng nhập tên của bạn để bắt đầu trò chơi:</p></div>",
        unsafe_allow_html=True,
    )
    username_input = st.text_input(
        "Tên hiển thị", placeholder="Nhập tên của bạn..."
    )
    if st.button("Vào Trò Chơi", use_container_width=True, type="primary"):
      if username_input.strip():
        name = username_input.strip()
        st.session_state.current_user = name
        if name not in st.session_state.users:
          st.session_state.users[name] = 1000  # Khởi tạo điểm Elo
        st.rerun()
      else:
        st.warning("Vui lòng nhập tên hợp lệ!")
  st.stop()

# ----------------- HEADER THÔNG TIN NGƯỜI CHƠI -----------------
user = st.session_state.current_user
user_score = st.session_state.users.get(user, 1000)

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
  st.markdown(
      f"🎮 Người chơi: **{user}** | ⭐ Điểm Elo: **`{user_score}`**",
      unsafe_allow_html=True,
  )
with col_h2:
  if st.button("Đổi người chơi"):
    st.session_state.current_user = ""
    st.rerun()

st.markdown(
    "<h1 style='text-align: center; margin-top: 5px;'>🪵 Cờ Caro Gỗ Trực Tuyến"
    " 🪵</h1>",
    unsafe_allow_html=True,
)

# ----------------- HỖ TRỢ CHƠI TRÊN 2 MÁY KHÁC NHAU QUA PHÒNG (URL QUERY PARAMS) -----------------
query_params = st.query_params
room_from_url = query_params.get("room", None)
if room_from_url:
  st.session_state.room_id = room_from_url

# ----------------- MENU LỰA CHỌN CHẾ ĐỘ & BẢNG XẾP HẠNG -----------------
tab1, tab2 = st.tabs(["🎮 Vào Trận Đấu", "🏆 Bảng Xếp Hạng & Lịch Sử"])

with tab2:
  col_tb1, col_tb2 = st.columns(2)
  with col_tb1:
    st.markdown("### 🏆 Top Điểm Elo Cao Nhất")
    if not st.session_state.users:
      st.info("Chưa có người chơi nào trên bảng xếp hạng.")
    else:
      sorted_users = sorted(
          st.session_state.users.items(), key=lambda x: x[1], reverse=True
      )
      for idx, (u_name, u_pts) in enumerate(sorted_users[:5], 1):
        medal = (
            "🥇"
            if idx == 1
            else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
        )
        st.markdown(f"{medal} **{u_name}** — `{u_pts} pts`")

  with col_tb2:
    st.markdown("### 📜 Lịch sử đấu gần đây")
    if not st.session_state.match_history:
      st.info("Chưa có trận đấu nào.")
    else:
      for match in st.session_state.match_history[-5:]:
        color_res = (
            "green"
            if match["result"] == "Thắng"
            else ("red" if match["result"] == "Thua" else "orange")
        )
        st.markdown(
            f"- {match['player']} vs {match['opponent']}:"
            f" <span style='color:{color_res}; font-weight:bold;'>{match['result']}</span>"
            f" (`{match['score']}`)",
            unsafe_allow_html=True,
        )

with tab1:
  # Chọn chế độ & Kích thước bàn cờ
  col_m1, col_m2 = st.columns(2)
  with col_m1:
    if st.button(
        "🤖 Đấu với Máy (AI)",
        use_container_width=True,
        type="primary"
        if st.session_state.game_mode == "vs_ai"
        else "secondary",
    ):
      st.session_state.game_mode = "vs_ai"
      st.session_state.board = [
          [" " for _ in range(st.session_state.size)]
          for _ in range(st.session_state.size)
      ]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.winning_line = []
      st.rerun()

  with col_m2:
    if st.button(
        "🌐 Đấu Online (2 Máy khác nhau)",
        use_container_width=True,
        type="primary"
        if st.session_state.game_mode == "online_pvp"
        else "secondary",
    ):
      st.session_state.game_mode = "online_pvp"
      st.session_state.board = [
          [" " for _ in range(st.session_state.size)]
          for _ in range(st.session_state.size)
      ]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.winning_line = []
      st.rerun()

  if st.session_state.game_mode == "online_pvp":
    st.markdown("---")
    st.markdown("### 🌐 Kết nối 2 máy khác nhau")
    st.info(
        "💡 **Cách chơi 2 máy:** Đặt tên phòng tùy ý hoặc dùng mặc định, sau đó"
        " bấm **Tham gia phòng** và copy đường dẫn trình duyệt gửi cho bạn bè"
        " mở trên máy của họ."
    )

    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
      entered_room = st.text_input(
          "Mã phòng chơi", value=st.session_state.room_id
      )
    with col_r2:
      st.markdown("<br>", unsafe_allow_html=True)
      if st.button("Tham gia phòng"):
        st.session_state.room_id = entered_room
        st.query_params["room"] = entered_room
        st.success(f"Đã vào phòng: {entered_room}!")
        st.rerun()

    st.markdown(f"🔗 **Mã phòng hiện tại:** `{st.session_state.room_id}`")

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
      st.session_state.board = [
          [" " for _ in range(10)] for _ in range(10)
      ]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.winning_line = []
      st.rerun()
  with col_s3:
    if st.button("📐 Bàn cờ 12x12 (Nối 5)", use_container_width=True):
      st.session_state.size = 12
      st.session_state.board = [
          [" " for _ in range(12)] for _ in range(12)
      ]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.winning_line = []
      st.rerun()

  size = st.session_state.size


  # ----------------- HÀM LOGIC GAME & TÌM ĐƯỜNG KẺ THẮNG -----------------
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
        if symbol != " " and all(
            b[r + k][c + k] == symbol for k in range(win_len)
        ):
          return symbol, [(r + k, c + k) for k in range(win_len)]
    # Chéo phụ
    for r in range(sz - win_len + 1):
      for c in range(win_len - 1, sz):
        symbol = b[r][c]
        if symbol != " " and all(
            b[r + k][c - k] == symbol for k in range(win_len)
        ):
          return symbol, [(r + k, c - k) for k in range(win_len)]
    return None, []


  def is_full(b, sz):
    return all(b[r][c] != " " for r in range(sz) for c in range(sz))


  def ai_move():
    best_move = None
    for r in range(size):
      for c in range(size):
        if st.session_state.board[r][c] == " ":
          has_neighbor = any(
              0 <= r + dr < size
              and 0 <= c + dc < size
              and st.session_state.board[r + dr][c + dc] != " "
              for dr in [-1, 0, 1]
              for dc in [-1, 0, 1]
          )
          if has_neighbor or size == 3:
            best_move = (r, c)
            break
      if best_move:
        break
    if not best_move:
      best_move = (size // 2, size // 2)

    st.session_state.board[best_move[0]][best_move[1]] = "O"
    w, line = check_winner(st.session_state.board, size)
    if w:
      st.session_state.winner = w
      st.session_state.winning_line = line
      if w == "O" and st.session_state.game_mode == "vs_ai":
        st.session_state.users[user] = max(
            100, st.session_state.users[user] - 10
        )
        st.session_state.match_history.append({
            "player": user,
            "opponent": "AI Robot",
            "result": "Thua",
            "score": "-10",
        })
    elif is_full(st.session_state.board, size):
      st.session_state.winner = "Draw"
      if st.session_state.game_mode == "vs_ai":
        st.session_state.match_history.append({
            "player": user,
            "opponent": "AI Robot",
            "result": "Hòa",
            "score": "0",
        })
    st.session_state.turn = "X"


  # Hiển thị trạng thái lượt đi
  mode_text = (
      "Đấu với Máy (AI)"
      if st.session_state.game_mode == "vs_ai"
      else "Đấu Online (2 Máy)"
  )
  if not st.session_state.winner:
    turn_msg = (
        f"Lượt đi: <b>{'Bạn (X)' if st.session_state.turn == 'X' else ('Máy (O)' if st.session_state.game_mode == 'vs_ai' else 'Đối thủ (O)')}</b>"
    )
  else:
    turn_msg = "Trận đấu đã kết thúc!"

  st.markdown(
      f"<div class='status-card'>🎮 Chế độ: <b>{mode_text}</b> (Phòng:"
      f" <code>{st.session_state.room_id}</code>) | {turn_msg}</div>",
      unsafe_allow_html=True,
  )

  # Hiển thị bàn cờ với hiệu ứng đường kẻ thắng
  st.markdown('<div class="chess-board-wrapper">', unsafe_allow_html=True)
  for r in range(size):
    cols = st.columns(size)
    for c in range(size):
      val = st.session_state.board[r][c]
      label = val if val != " " else ""
      is_winning_cell = (r, c) in st.session_state.winning_line

      if is_winning_cell:
        with cols[c]:
          st.markdown(
              f'<div class="win-cell"><button>{label}</button></div>',
              unsafe_allow_html=True,
          )
      else:
        if cols[c].button(label, key=f"btn_{r}_{c}"):
          if val == " " and not st.session_state.winner:
            current_player = st.session_state.turn
            st.session_state.board[r][c] = current_player

            w, line = check_winner(st.session_state.board, size)
            if w:
              st.session_state.winner = w
              st.session_state.winning_line = line
              if st.session_state.game_mode == "vs_ai":
                if w == "X":
                  st.session_state.users[user] += 15
                  st.session_state.match_history.append({
                      "player": user,
                      "opponent": "AI Robot",
                      "result": "Thắng",
                      "score": "+15",
                  })
              elif st.session_state.game_mode == "online_pvp":
                st.session_state.match_history.append({
                    "player": user,
                    "opponent": "Bạn bè",
                    "result": "Thắng" if w == "X" else "Thua",
                    "score": "+15",
                })
            elif is_full(st.session_state.board, size):
              st.session_state.winner = "Draw"
            else:
              if st.session_state.game_mode == "vs_ai":
                st.session_state.turn = "O"
                ai_move()
              else:
                st.session_state.turn = "O" if current_player == "X" else "X"
            st.rerun()
  st.markdown("</div>", unsafe_allow_html=True)

  # Thông báo kết quả
  if st.session_state.winner:
    if st.session_state.winner == "X":
      st.success(
          "🎉 Chúc mừng bạn (X) đã chiến thắng! Đường kẻ chiến thắng đã được"
          " tô sáng."
      )
    elif st.session_state.winner == "O":
      st.error("🤖 Đối thủ / AI (O) đã giành chiến thắng!")
    else:
      st.warning("🤝 Trận đấu hòa!")

  # Nút chơi lại
  r_col1, r_col2, r_col3 = st.columns([2, 1, 2])
  with r_col2:
    if st.button("🔄 Chơi Ván Mới", use_container_width=True, type="primary"):
      st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.winning_line = []
      st.rerun()
