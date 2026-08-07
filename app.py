import streamlit as st

st.set_page_config(page_title="Cờ Caro AI", page_icon="❌⭕", layout="centered")

# Khởi tạo trạng thái game trước để lấy kích thước `size`
if "board" not in st.session_state:
  st.session_state.size = 3
  st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
  st.session_state.turn = "X"
  st.session_state.winner = None

current_size = st.session_state.size

# CSS Grid động theo kích thước bàn cờ
css_code = f"""
<style>
div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) {{
    display: flex;
    justify-content: center;
}}

div[data-testid="stHorizontalBlock"] {{
    display: grid !important;
    grid-template-columns: repeat({current_size}, 55px) !important;
    gap: 0px !important;
    width: max-content !important;
}}

div[data-testid="column"] {{
    width: 55px !important;
    flex: unset !important;
    min-width: unset !important;
    padding: 0 !important;
}}

div.stButton > button {{
    width: 55px !important;
    height: 55px !important;
    font-size: 24px;
    font-weight: bold;
    border-radius: 0px !important;
    border: 1px solid #1f77b4 !important;
    margin: 0 !important;
    background-color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
}}

div.stButton > button:hover {{
    border-color: #ff4b4b !important;
    background-color: #f0f2f6;
}}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

st.title("🎮 Cờ Caro AI (Minimax & Alpha-Beta)")


def check_winner(b, size):
  # Kiểm tra hàng ngang
  for r in range(size):
    for c in range(size - 2):
      # Nếu size = 4 cần 4 ô, size = 3 cần 3 ô liên tiếp
      win_len = 3 if size == 3 else 4
      if c + win_len <= size:
        symbol = b[r][c]
        if symbol != " ":
          if all(b[r][c + k] == symbol for k in range(win_len)):
            return symbol

  # Kiểm tra hàng dọc
  for c in range(size):
    for r in range(size - 2):
      win_len = 3 if size == 3 else 4
      if r + win_len <= size:
        symbol = b[r][c]
        if symbol != " ":
          if all(b[r + k][c] == symbol for k in range(win_len)):
            return symbol

  # Kiểm tra đường chéo chính (\)
  win_len = 3 if size == 3 else 4
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


def minimax(board, depth, is_maximizing, alpha, beta, size, max_depth):
  winner = check_winner(board, size)
  if winner == "O":
    return 10 - depth
  if winner == "X":
    return depth - 10
  if is_full(board, size) or depth == max_depth:
    return 0

  if is_maximizing:
    max_eval = -float("inf")
    for r in range(size):
      for c in range(size):
        if board[r][c] == " ":
          board[r][c] = "O"
          eval = minimax(
              board, depth + 1, False, alpha, beta, size, max_depth
          )
          board[r][c] = " "
          max_eval = max(max_eval, eval)
          alpha = max(alpha, eval)
          if beta <= alpha:
            break
    return max_eval
  else:
    min_eval = float("inf")
    for r in range(size):
      for c in range(size):
        if board[r][c] == " ":
          board[r][c] = "X"
          eval = minimax(board, depth + 1, True, alpha, beta, size, max_depth)
          board[r][c] = " "
          min_eval = min(min_eval, eval)
          beta = min(beta, eval)
          if beta <= alpha:
            break
    return min_eval


def ai_move():
  size = st.session_state.size
  best_score = -float("inf")
  best_move = None
  # Giới hạn độ sâu minimax để tránh đơ máy với bảng 4x4
  max_depth = 3 if size == 4 else 4

  for r in range(size):
    for c in range(size):
      if st.session_state.board[r][c] == " ":
        st.session_state.board[r][c] = "O"
        score = minimax(
            st.session_state.board,
            0,
            False,
            -float("inf"),
            float("inf"),
            size,
            max_depth,
        )
        st.session_state.board[r][c] = " "
        if score > best_score:
          best_score = score
          best_move = (r, c)

  if best_move:
    st.session_state.board[best_move[0]][best_move[1]] = "O"
    w = check_winner(st.session_state.board, size)
    if w:
      st.session_state.winner = w
    elif is_full(st.session_state.board, size):
      st.session_state.winner = "Draw"
    st.session_state.turn = "X"


# Chọn kích thước bàn cờ
col1, col2 = st.columns(2)
with col1:
  if st.button("Chơi 3x3"):
    st.session_state.size = 3
    st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()
with col2:
  if st.button("Chơi 4x4"):
    st.session_state.size = 4
    st.session_state.board = [[" " for _ in range(4)] for _ in range(4)]
    st.session_state.turn = "X"
    st.session_state.winner = None
    st.rerun()

size = st.session_state.size
st.write(
    f"Trạng thái: **{'Lượt của bạn (X)' if st.session_state.turn == 'X' else'AI đang đi...'
    }**"
)

# Hiển thị bàn cờ
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

if st.button("Chơi lại từ đầu"):
  st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
  st.session_state.turn = "X"
  st.session_state.winner = None
  st.rerun()
