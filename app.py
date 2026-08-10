import streamlit as st

st.set_page_config(
    page_title="Cờ Caro Gỗ Trực Tuyến", page_icon="🪵", layout="centered"
)

# Khởi tạo trạng thái game
if "board" not in st.session_state:
  st.session_state.size = 10
  st.session_state.board = [
      [" " for _ in range(10)] for _ in range(10)
  ]
  st.session_state.turn = "X"
  st.session_state.winner = None
  st.session_state.game_mode = "vs_ai"  # Mặc định chơi với máy: 'vs_ai' hoặc 'vs_player'

current_size = st.session_state.size

# Giao diện CSS hiện đại, bo góc mềm mại, đổ bóng sang trọng
css_code = f"""
<style>
/* Toàn cục */
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 800px;
    background-color: #fcf9f2;
    border-radius: 16px;
}}

/* Tiêu đề trang */
h1 {{
    color: #5c4033;
    font-family: 'Helvetica Neue', sans-serif;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
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

/* Ép các hàng nút bàn cờ thành lưới chuẩn */
.chess-board-wrapper div[data-testid="stHorizontalBlock"] {{
    display: grid !important;
    grid-template-columns: repeat({current_size}, 42px) !important;
    gap: 0px !important;
    width: max-content !important;
    margin: 0 !important;
}}

.chess-board-wrapper div[data-testid="column"] {{
    width: 42px !important;
    flex: unset !important;
    min-width: unset !important;
    padding: 0 !important;
}}

/* Nút ô cờ */
.chess-board-wrapper div.stButton > button {{
    width: 42px !important;
    height: 42px !important;
    font-size: 20px;
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

/* Thẻ trạng thái lượt đi */
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

# Tiêu đề ứng dụng
st.markdown(
    "<h1 style='text-align: center;'>🪵 Cờ Caro Gỗ Trực Tuyến 🪵</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #7f5539; font-weight: 500;'>Trải"
    " nghiệm giải trí đỉnh cao với giao diện mộc mạc, tinh tế</p>",
    unsafe_allow_html=True,
)

# ----------------- THANH MENU ĐIỀU KHIỂN & CHẾ ĐỘ -----------------
st.markdown("---")
col_mode1, col_mode2 = st.columns(2)

with col_mode1:
  if st.button(
      "🤖 Chế độ: Đấu với Máy (AI)",
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
    st.rerun()

with col_mode2:
  if st.button(
      "👥 Chế độ: Đấu với Bạn (2 Người)",
      use_container_width=True,
      type="primary"
      if st.session_state.game_mode == "vs_player"
      else "secondary",
  ):
    st.session_state.game_mode = "vs_player"
    st.session_state.board = [
        [" " for _ in range(st.session_state.size)]
        for _ in range(st.session_state.size)
    ]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()

# Chọn kích thước bàn cờ
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
  if st.button("📐 Bàn cờ 3x3 (Nối 3)", use_container_width=True):
    st.session_state.size = 3
    st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
with col_s2:
  if st.button("📐 Bàn cờ 10x10 (Nối 5)", use_container_width=True):
    st.session_state.size = 10
    st.session_state.board = [[" " for _ in range(10)] for _ in range(10)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
with col_s3:
  if st.button("📐 Bàn cờ 12x12 (Nối 5)", use_container_width=True):
    st.session_state.size = 12
    st.session_state.board = [[" " for _ in range(12)] for _ in range(12)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()

size = st.session_state.size

# ----------------- HÀM LOGIC GAME -----------------
def check_winner(b, sz):
  win_len = 3 if sz == 3 else 5
  for r in range(sz):
    for c in range(sz - win_len + 1):
      symbol = b[r][c]
      if symbol != " " and all(b[r][c + k] == symbol for k in range(win_len)):
        return symbol
  for c in range(sz):
    for r in range(sz - win_len + 1):
      symbol = b[r][c]
      if symbol != " " and all(b[r + k][c] == symbol for k in range(win_len)):
        return symbol
  for r in range(sz - win_len + 1):
    for c in range(sz - win_len + 1):
      symbol = b[r][c]
      if symbol != " " and all(b[r + k][c + k] == symbol for k in range(win_len)):
        return symbol
  for r in range(sz - win_len + 1):
    for c in range(win_len - 1, sz):
      symbol = b[r][c]
      if symbol != " " and all(b[r + k][c - k] == symbol for k in range(win_len)):
        return symbol
  return None


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
  w = check_winner(st.session_state.board, size)
  if w:
    st.session_state.winner = w
  elif is_full(st.session_state.board, size):
    st.session_state.winner = "Draw"
  st.session_state.turn = "X"


# ----------------- HIỂN THỊ TRẠNG THÁI & BÀN CỜ -----------------
mode_text = (
    "Đấu với Máy (AI)"
    if st.session_state.game_mode == "vs_ai"
    else "Đấu 2 Người (PvP)"
)
if not st.session_state.winner:
  turn_msg = (
      f"Lượt đi: <b>{'Bạn (X)' if st.session_state.turn == 'X' else 'Máy (O)'}</b>"
      if st.session_state.game_mode == "vs_ai"
      else f"Lượt đi: <b>{'Người chơi 1 (X)' if st.session_state.turn == 'X' else 'Người chơi 2 (O)'}</b>"
  )
else:
  turn_msg = "Trận đấu đã kết thúc!"

st.markdown(
    f"<div class='status-card'>🎮 Chế độ: <b>{mode_text}</b> | {turn_msg}</div>",
    unsafe_allow_html=True,
)

# Hiển thị bàn cờ liền mạch trong khung gỗ
st.markdown('<div class="chess-board-wrapper">', unsafe_allow_html=True)
for r in range(size):
  cols = st.columns(size)
  for c in range(size):
    val = st.session_state.board[r][c]
    label = val if val != " " else ""
    if cols[c].button(label, key=f"btn_{r}_{c}"):
      if val == " " and not st.session_state.winner:
        current_player = st.session_state.turn
        st.session_state.board[r][c] = current_player

        w = check_winner(st.session_state.board, size)
        if w:
          st.session_state.winner = w
        elif is_full(st.session_state.board, size):
          st.session_state.winner = "Draw"
        else:
          # Đổi lượt hoặc gọi AI
          if st.session_state.game_mode == "vs_ai":
            st.session_state.turn = "O"
            ai_move()
          else:
            st.session_state.turn = "O" if current_player == "X" else "X"
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ----------------- THÔNG BÁO KẾT QUẢ & NÚT CHƠI LẠI -----------------
if st.session_state.winner:
  if st.session_state.winner == "X":
    win_ann = (
        "🎉 Chúc mừng! Bạn (X) đã giành chiến thắng!"
        if st.session_state.game_mode == "vs_ai"
        else "🎉 Chúc mừng Người chơi 1 (X) đã giành chiến thắng!"
    )
    st.success(win_ann)
  elif st.session_state.winner == "O":
    win_ann = (
        "🤖 AI (O) đã giành chiến thắng! Thử lại nhé."
        if st.session_state.game_mode == "vs_ai"
        else "🎉 Chúc mừng Người chơi 2 (O) đã giành chiến thắng!"
    )
    st.error(win_ann)
  else:
    st.warning("🤝 Trận đấu kết thúc với kết quả Hòa!")

col_r1, col_r2, col_r3 = st.columns([2, 1, 2])
with col_r2:
  if st.button("🔄 Chơi Ván Mới", use_container_width=True, type="primary"):
    st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
