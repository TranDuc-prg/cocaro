import streamlit as st

st.set_page_config(page_title="Cờ Caro AI", page_icon="❌⭕", layout="centered")

# CSS sử dụng Grid để ép các ô dính sát khít tuyệt đối không khoảng trống
st.markdown(
    """
    <style>
    /* Ẩn cấu trúc cột mặc định của Streamlit trong bàn cờ và chuyển thành CSS Grid */
    div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) {
        display: flex;
        justify-content: center;
    }
    
    /* Gom các cột thành một khối lưới duy nhất sát khít */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(3, 60px) !important;
        gap: 0px !important;
        width: max-content !important;
    }
    
    div[data-testid="column"] {
        width: 60px !important;
        flex: unset !important;
        min-width: unset !important;
        padding: 0 !important;
    }

    /* Tùy chỉnh nút bấm vuông vắn, dính liền viền nhau */
    div.stButton > button {
        width: 60px !important;
        height: 60px !important;
        font-size: 26px;
        font-weight: bold;
        border-radius: 0px !important;
        border: 1px solid #1f77b4 !important;
        margin: 0 !important;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    div.stButton > button:hover {
        border-color: #ff4b4b !important;
        background-color: #f0f2f6;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🎮 Cờ Caro AI (Minimax & Alpha-Beta)")

# Khởi tạo trạng thái game trong Streamlit
if "board" not in st.session_state:
  st.session_state.size = 3
  st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
  st.session_state.turn = "X"  # X: Người, O: AI
  st.session_state.winner = None


def check_winner(b, size):
  for i in range(size):
    if all(b[i][j] == b[i][0] and b[i][0] != " " for j in range(size)):
      return b[i][0]
    if all(b[j][i] == b[0][i] and b[0][i] != " " for j in range(size)):
      return b[0][i]
  if all(b[i][i] == b[0][0] and b[0][0] != " " for i in range(size)):
    return b[0][0]
  if all(
      b[i][size - 1 - i] == b[0][size - 1] and b[0][size - 1] != " "
      for i in range(size)
  ):
    return b[0][size - 1]
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
  max_depth = 4 if size == 3 else 2

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
    st.session_state.turn = "X"


# Chọn kích thước bàn cờ
col1, col2 = st.columns(2)
with col1:
  if st.button("Chơi 3x3"):
    st.session_state.size = 3
    st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
    st.session_state.turn = "X"
    st.session_state.winner = None
with col2:
  if st.button("Chơi 4x4"):
    st.session_state.size = 4
    st.session_state.board = [[" " for _ in range(4)] for _ in range(4)]
    st.session_state.turn = "X"
    st.session_state.winner = None

size = st.session_state.size
st.write(
    f"Trạng thái: **{'Lượt của bạn (X)' if st.session_state.turn == 'X' else'AI đang đi...'
    }**"
)

# Hiển thị bàn cờ dạng lưới dính liền sát khít
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
