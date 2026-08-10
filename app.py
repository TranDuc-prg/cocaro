import streamlit as st

st.set_page_config(
    page_title="Cờ Caro Gỗ", page_icon="🪵", layout="centered"
)

# Khởi tạo trạng thái game (Mặc định 10x10)
if "board" not in st.session_state:
  st.session_state.size = 10
  st.session_state.board = [
      [" " for _ in range(10)] for _ in range(10)
  ]
  st.session_state.turn = "X"
  st.session_state.winner = None

current_size = st.session_state.size

# CSS Grid chuẩn xác giúp bàn cờ dính liền sát khít thành một khối thống nhất
css_code = f"""
<style>
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 1.5rem;
    max-width: 700px;
}}

/* Gom toàn bộ các hàng của bàn cờ thành một khối lưới duy nhất */
div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) {{
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: #d2b48c;
    border: 4px solid #8b4513;
    padding: 4px;
    width: max-content;
    margin: 0 auto;
    border-radius: 4px;
}}

div[data-testid="stHorizontalBlock"] {{
    display: grid !important;
    grid-template-columns: repeat({current_size}, 42px) !important;
    gap: 0px !important;
    width: max-content !important;
    margin: 0 !important;
}}

div[data-testid="column"] {{
    width: 42px !important;
    flex: unset !important;
    min-width: unset !important;
    padding: 0 !important;
}}

div.stButton > button {{
    width: 42px !important;
    height: 42px !important;
    font-size: 20px;
    font-weight: bold;
    border-radius: 0px !important;
    border: 1px solid #c8ad7f !important;
    margin: 0 !important;
    background-color: #fdf5e6;
    color: #333333;
    display: flex;
    align-items: center;
    justify-content: center;
}}

div.stButton > button:hover {{
    border-color: #8b4513 !important;
    background-color: #faebd7;
}}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

st.markdown(
    "<h1 style='text-align: center; color: #5c4033;'>🪵 Cờ Caro Gỗ 🪵</h1>",
    unsafe_allow_html=True,
)


def check_winner(b, size):
  win_len = 3 if size == 3 else 5

  # Kiểm tra hàng ngang
  for r in range(size):
    for c in range(size - win_len + 1):
      symbol = b[r][c]
      if symbol != " ":
        if all(b[r][c + k] == symbol for k in range(win_len)):
          return symbol

  # Kiểm tra hàng dọc
  for c in range(size):
    for r in range(size - win_len + 1):
      symbol = b[r][c]
      if symbol != " ":
        if all(b[r + k][c] == symbol for k in range(win_len)):
          return symbol

  # Kiểm tra đường chéo chính (\)
  for r in range(size - win_len + 1):
    for c in range(size - win_len + 1):
      symbol = b[r][c]
      if symbol != " ":
        if all(b[r + k][c + k] == symbol for k in range(win_len)):
          return symbol

  # Kiểm tra đường chéo phụ (/)
  for r in range(size - win_len + 1):
    for c in range(win_len - 1, size):
      symbol = b[r][c]
      if symbol != " ":
        if all(b[r + k][c - k] == symbol for k in range(win_len)):
          return symbol

  return None


def is_full(b, size):
  for r in range(size):
    for c in range(size):
      if b[r][c] == " ":
        return False
  return True


def ai_move():
  size = st.session_state.size
  best_move = None

  for r in range(size):
    for c in range(size):
      if st.session_state.board[r][c] == " ":
        has_neighbor = False
        for dr in [-1, 0, 1]:
          for dc in [-1, 0, 1]:
            nr, nc = r + dr, c + dc
            if (
                0 <= nr < size
                and 0 <= nc < size
                and st.session_state.board[nr][nc] != " "
            ):
              has_neighbor = True
        if has_neighbor:
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


# Chọn kích thước bàn cờ (3x3, 10x10, 12x12)
col1, col2, col3 = st.columns(3)
with col1:
  if st.button("Chơi 3x3", use_container_width=True):
    st.session_state.size = 3
    st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
with col2:
  if st.button("Chơi 10x10", use_container_width=True):
    st.session_state.size = 10
    st.session_state.board = [[" " for _ in range(10)] for _ in range(10)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
with col3:
  if st.button("Chơi 12x12", use_container_width=True):
    st.session_state.size = 12
    st.session_state.board = [[" " for _ in range(12)] for _ in range(12)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()

size = st.session_state.size
st.markdown(
    f"<p style='text-align: center; font-size: 16px;'>Trạng thái: <b>{'Lượt của bạn (X)' if st.session_state.turn == 'X' else 'AI đang đi...'}</b></p>",
    unsafe_allow_html=True,
)

# Hiển thị bàn cờ liền mạch
for r in range(size):
  cols = st.columns(size)
  for c in range(size):
    val = st.session_state.board[r][c]
    label = val if val != " " else ""
    if cols[c].button(label, key=f"btn_{r}_{c}"):
      if (
          val == " "
          and st.session_state.turn == "X"
          and not st.session_state.winner
      ):
        st.session_state.board[r][c] = "X"
        if check_winner(st.session_state.board, size) == "X":
          st.session_state.winner = "X"
        elif is_full(st.session_state.board, size):
          st.session_state.winner = "Draw"
        else:
          st.session_state.turn = "O"
          ai_move()
        st.rerun()

# Thông báo kết quả
if st.session_state.winner:
  if st.session_state.winner == "X":
    st.success("🎉 Chúc mừng! Bạn đã chiến thắng!")
  elif st.session_state.winner == "O":
    st.error("🤖 AI đã chiến thắng!")
  else:
    st.warning("🤝 Trận đấu hòa!")

# Nút chơi lại
r_col1, r_col2, r_col3 = st.columns([2, 1, 2])
with r_col2:
  if st.button("Chơi lại", use_container_width=True):
    st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
