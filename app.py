import streamlit as st

st.set_page_config(
    page_title="Cờ Caro Trực Tuyến", page_icon="🪵", layout="wide"
)

# Khởi tạo cơ sở dữ liệu giả lập trong session_state
if "users" not in st.session_state:
  st.session_state.users = {
      "ppppp": 1900,
      "12345": 1705,
      "CrazyRubik": 1660,
      "Ani": 1645,
      "Hoàng Thời": 1630,
  }

if "match_history" not in st.session_state:
  st.session_state.match_history = [
      {
          "player": "ppppp",
          "opponent": "AI Robot",
          "result": "Thắng",
          "score": "+15",
      },
      {"player": "12345", "opponent": "AI Robot", "result": "Thua", "score": "-10"},
  ]

if "current_user" not in st.session_state:
  st.session_state.current_user = ""

if "board" not in st.session_state:
  st.session_state.size = 10
  st.session_state.board = [
      [" " for _ in range(10)] for _ in range(10)
  ]
  st.session_state.turn = "X"
  st.session_state.winner = None
  st.session_state.game_mode = "menu"

current_size = st.session_state.size

# Giao diện CSS đồng bộ bàn cờ gỗ liền mạch và các thẻ card tinh tế
css_code = f"""
<style>
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px !important;
}}

/* Khung bàn cờ gỗ liền mạch chuẩn xác */
div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]) {{
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: #d2b48c;
    border: 4px solid #8b4513;
    padding: 6px;
    width: max-content;
    margin: 0 auto;
    border-radius: 8px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
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

.custom-card {{
    background-color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 20px;
    border: 1px solid #eaeaea;
}}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# Màn hình đăng nhập tên người chơi
if not st.session_state.current_user:
  st.markdown(
      "<h2 style='text-align: center; color: #5c4033;'>🪵 Cờ Caro Gỗ Trực"
      " Tuyến 🪵</h2>",
      unsafe_allow_html=True,
  )
  _, col_login, _ = st.columns([1, 2, 1])
  with col_login:
    st.markdown(
        "<div class='custom-card'><h3>Bạn là ai?</h3><p>Vui lòng nhập tên"
        " người dùng để lưu điểm Elo và lịch sử đấu:</p></div>",
        unsafe_allow_html=True,
    )
    username_input = st.text_input("Tên người dùng", placeholder="Nhập tên...")
    if st.button("Vào trò chơi", use_container_width=True):
      if username_input.strip():
        name = username_input.strip()
        st.session_state.current_user = name
        if name not in st.session_state.users:
          st.session_state.users[name] = 1000
        st.rerun()
      else:
        st.warning("Vui lòng nhập tên hợp lệ!")
  st.stop()

# Thông tin header người chơi hiện tại
user = st.session_state.current_user
user_score = st.session_state.users[user]

col_h1, col_h2, col_h3 = st.columns([3, 6, 2])
with col_h1:
  st.markdown(
      f"👤 Người chơi: **{user}** | Elo: `⭐ {user_score}`",
      unsafe_allow_html=True,
  )
with col_h3:
  if st.button("Đổi người chơi"):
    st.session_state.current_user = ""
    st.rerun()

st.markdown(
    "<h1 style='text-align: center; color: #5c4033; margin-top: 10px;'>🪵 Cờ"
    " Caro Gỗ 🪵</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #666;'>Người đầu tiên nối đủ quân"
    " cờ theo quy định sẽ giành chiến thắng</p>",
    unsafe_allow_html=True,
)

# Menu chọn chế độ chơi và hiển thị bảng xếp hạng / lịch sử
if st.session_state.game_mode == "menu":
  col_m1, col_m2 = st.columns([1.5, 1])

  with col_m1:
    st.markdown("### 🕹️ Chọn chế độ chơi")
    if st.button("🪵 Chơi với Robot - Bàn Cờ 3x3 (Nối 3)", use_container_width=True):
      st.session_state.size = 3
      st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.game_mode = "3x3"
      st.rerun()

    if st.button(
        "🪵 Chơi với Robot - Bàn Cờ Gỗ 10x10 (Nối 5)", use_container_width=True
    ):
      st.session_state.size = 10
      st.session_state.board = [
          [" " for _ in range(10)] for _ in range(10)
      ]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.game_mode = "10x10"
      st.rerun()

    if st.button(
        "🪵 Chơi với Robot - Bàn Cờ Gỗ 12x12 (Nối 5)", use_container_width=True
    ):
      st.session_state.size = 12
      st.session_state.board = [
          [" " for _ in range(12)] for _ in range(12)
      ]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.session_state.game_mode = "12x12"
      st.rerun()

  with col_m2:
    st.markdown("### 🏆 Bảng Xếp Hạng Elo")
    sorted_users = sorted(
        st.session_state.users.items(), key=lambda x: x[1], reverse=True
    )
    for idx, (u_name, u_pts) in enumerate(sorted_users[:5], 1):
      medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
      st.markdown(f"{medal} **{u_name}** — `{u_pts} pts`")

    st.markdown("### 📜 Lịch sử đấu gần đây")
    for match in st.session_state.match_history[-3:]:
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

else:
  # Giao diện khi đang trong trận đấu
  size = st.session_state.size


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
      if w == "O":
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
      st.session_state.match_history.append({
          "player": user,
          "opponent": "AI Robot",
          "result": "Hòa",
          "score": "0",
      })
    st.session_state.turn = "X"


  col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
  with col_b2:
    if st.button("⬅️ Quay lại Menu chính", use_container_width=True):
      st.session_state.game_mode = "menu"
      st.rerun()

  st.markdown(
      f"<p style='text-align: center; font-size: 16px; margin: 10px 0;'>Trạng"
      f" thái: <b>{'Lượt của bạn (X)' if st.session_state.turn == 'X' else 'AI đang đi (O)...'}</b></p>",
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
          w = check_winner(st.session_state.board, size)
          if w == "X":
            st.session_state.winner = "X"
            st.session_state.users[user] += 15
            st.session_state.match_history.append({
                "player": user,
                "opponent": "AI Robot",
                "result": "Thắng",
                "score": "+15",
            })
          elif is_full(st.session_state.board, size):
            st.session_state.winner = "Draw"
            st.session_state.match_history.append({
                "player": user,
                "opponent": "AI Robot",
                "result": "Hòa",
                "score": "0",
            })
          else:
            st.session_state.turn = "O"
            ai_move()
          st.rerun()

  # Thông báo kết quả trò chơi
  if st.session_state.winner:
    if st.session_state.winner == "X":
      st.success("🎉 Chúc mừng! Bạn đã chiến thắng (+15 Elo)!")
    elif st.session_state.winner == "O":
      st.error("🤖 AI đã chiến thắng! (-10 Elo)")
    else:
      st.warning("🤝 Trận đấu hòa!")

  _, r_btn, _ = st.columns([2, 1, 2])
  with r_btn:
    if st.button("Chơi ván mới", use_container_width=True):
      st.session_state.board = [[" " for _ in range(size)] for _ in range(size)]
      st.session_state.turn = "X"
      st.session_state.winner = None
      st.rerun()
