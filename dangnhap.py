# dangnhap.py (Đã nâng cấp giao diện siêu đẹp, hiện đại & fix lỗi role admin)
import streamlit as st
from db import get_user
import time

def render_login_page():
    # Inject CSS tùy chỉnh phong cách gỗ cao cấp & hiện đại
    st.markdown("""
        <style>
        .login-container {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(245, 235, 220, 0.85));
            padding: 40px 30px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
            border: 2px solid #e0c9a6;
            backdrop-filter: blur(10px);
            margin-top: 20px;
        }
        .login-title {
            text-align: center;
            color: #5c3a21;
            font-weight: 800;
            font-size: 28px;
            margin-bottom: 25px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        .main-banner {
            text-align: center;
            font-size: 38px;
            font-weight: 900;
            color: #4a3525;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.15);
            margin-bottom: 10px;
        }
        .stButton>button {
            background: linear-gradient(135deg, #8d5b4c, #5c3a21);
            color: white;
            font-weight: bold;
            border-radius: 12px;
            border: none;
            padding: 12px;
            box-shadow: 0 4px 12px rgba(92, 58, 33, 0.3);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #a66e5d, #70472a);
            box-shadow: 0 6px 16px rgba(92, 58, 33, 0.4);
            transform: translateY(-2px);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-banner">🪵 Cờ Caro Gỗ Trực Tuyến 🪵</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7f634d; font-size: 16px; margin-bottom: 30px;'>Trải nghiệm đỉnh cao cùng trí tuệ nhân tạo và bạn bè</p>", unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.3, 1])
    with col_login:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🎯 Đăng Nhập Hệ Thống</div>', unsafe_allow_html=True)
       
        username_input = st.text_input("Tên tài khoản", placeholder="Nhập tên đăng nhập của bạn", key="login_user")
        password_input = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu bảo mật", key="login_pass")
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
       
        if st.button("🚀 Vào Trận Đấu Ngay", use_container_width=True):
            if username_input.strip() and password_input.strip():
                name = username_input.strip()
                user_data = get_user(name)
                
                if user_data and user_data.get('password') == password_input.strip():
                    st.session_state.current_user = name
                    
                    # CƠ CHẾ AN TOÀN: Nếu tài khoản là 'duc' hoặc các tài khoản admin chính, ép cứng role là 'admin'
                    # Hoặc lấy trực tiếp từ database nếu cột role đã được set chuẩn 'admin'
                    fetched_role = user_data.get('role', 'user')
                    if name.lower() in ['duc', 'admin']: 
                        st.session_state.user_role = 'admin'
                    else:
                        st.session_state.user_role = fetched_role

                    st.session_state.game_mode = "vs_ai"
                    st.session_state.size = 3
                    st.session_state.board = [[" " for _ in range(3)] for _ in range(3)]
                    st.session_state.turn = "X"
                    st.session_state.winner = None
                    st.session_state.winning_line = []
                    st.session_state.win_score = None
                    st.session_state.show_winner_overlay = False
                    st.session_state.room_id = "phong_mac_dinh"
                    st.session_state.my_symbol = "X"
                    st.session_state.is_room_creator = False
                    st.session_state.elo_updated_online = False
                    st.session_state.ai_stats = None
                    st.session_state.hint_move = None
                    st.session_state.board_history = []
                    st.session_state.last_move = None
                    st.session_state.ai_difficulty = "Trung bình"
                    st.session_state.turn_start_time = time.time()
                    st.session_state['trigger_rerun'] = True
                else:
                    st.error("❌ Tên tài khoản hoặc mật khẩu không chính xác.")
            else:
                st.warning("⚠️ Vui lòng điền đầy đủ thông tin để tiếp tục.")
        st.markdown('</div>', unsafe_allow_html=True)