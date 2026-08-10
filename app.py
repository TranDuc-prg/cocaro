import streamlit as st

st.set_page_config(
    page_title="Cờ Caro AI - Bàn Cờ Lớn", page_icon="❌⭕", layout="wide"
)

# Khởi tạo trạng thái game (Mặc định bàn cờ lớn 10x10)
if "board" not in st.session_state:
  st.session_state.size = 10
  st.session_state.board = [
      [" " for _ in range(10)] for _ in range(10)
  ]
  st.session_state.turn = "X"  # X: Người, O: AI
  st.session_state.winner = None

current_size = st.session_state.size

# CSS Grid động tạo khung bàn cờ liền mạch, màu vân gỗ sáng sang trọng
css_code = f"""
<style>
.block-container {{
    padding-top: 1rem;
    padding-bottom: 1rem;
    max-width: 1000px;
}}

div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) {{
    display: flex;
    justify-content: center;
}}

div[data-testid="stHorizontalBlock"] {{
    display: grid !important;
    grid-template-columns: repeat({current_size}, 42px) !important;
    gap: 0px !important;
    width: max-content !important;
    background-color: #d2b48c;
    border: 3px solid #8b4513;
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
    "<h1 style='text-align: center;'>🪵 Cờ Caro Gỗ (Kẻ Ô Lớn)</h1>",
    unsafe_allow_html=True,
)


def check_winner(b, size, win_len=5):
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


# Thuật toán AI đơn giản quét ô trống gần quân cờ cho bàn cờ lớn
def ai_move():
  size = st.session_state.size
  best_move = None

  # Ưu tiên đánh gần các ô đã có quân
  for r in range(size):
    for c in range(size):
      if st.session_state.board[r][c] == " ":
        # Kiểm tra xem xung quanh có quân cờ nào không
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

  # Nếu bàn cờ trống thì đánh vào giữa
  if not best_move:
    best_move = (size // 2, size // 2)

  st.session_state.board[best_move[0]][best_move[1]] = "O"
  w = check_winner(st.session_state.board, size, win_len=5)
  if w:
    st.session_state.winner = w
  elif is_full(st.session_state.board, size):
    st.session_state.winner = "Draw"
  st.session_state.turn = "X"


# Chọn kích thước bàn cờ
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
with col_m2:
  b_col1, b_col2 = st.columns(2)
  with b_col1:
    if st.button("Bàn Cờ 10x10", use_container_width=True):
      st.session_state.size = 10
      st.session_state.board = [[" " for _ in range(10)] for _ in range(10)]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.rerun()
  with b_col2:
    if st.button("Bàn Cờ 12x12", use_container_width=True):
      st.session_state.size = 12
      st.session_state.board = [[" " for _ in range(12)] for _ in range(12)]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.rerun()

size = st.session_state.size
st.markdown(
    f"<p style='text-align: center;'>Trạng thái: <b>{'Lượt của bạn (X)' if st.session_state.turn == 'X' else'AI đang đi...'}</b></p>",
    unsafe_allow_html=True,
)

# Hiển thị bàn cờ lớn dạng lưới gỗ
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
        if check_winner(st.session_state.board, size, win_len=5) == "X":
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

# Nút chơi lại căn giữa
r_col1, r_col2, r_col3 = st.columns([2, 1, 2])
with r_col2:
  if st.button("Chơi lại từ đầu", use_container_width=True):
    st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
