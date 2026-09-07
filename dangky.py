# dangky.py (Đã nâng cấp giao diện siêu đẹp, đồng bộ phong cách)
import streamlit as st
from db import get_user, create_user

def render_register_page():
    # Inject CSS đồng bộ với trang đăng nhập
    st.markdown("""
        <style>
        .register-container {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(245, 235, 220, 0.85));
            padding: 40px 30px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
            border: 2px solid #e0c9a6;
            backdrop-filter: blur(10px);
            margin-top: 20px;
        }
        .register-title {
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
    st.markdown("<p style='text-align: center; color: #7f634d; font-size: 16px; margin-bottom: 30px;'>Tạo tài khoản ngay để lưu lại thành tích và điểm ELO của bạn</p>", unsafe_allow_html=True)

    _, col_reg, _ = st.columns([1, 1.3, 1])
    with col_reg:
        st.markdown('<div class="register-container">', unsafe_allow_html=True)
        st.markdown('<div class="register-title">🎯 Đăng Ký Tài Khoản</div>', unsafe_allow_html=True)
        
        new_user = st.text_input("Tên tài khoản", placeholder="Chọn tên tài khoản độc đáo", key="reg_user")
        new_pass = st.text_input("Mật khẩu", type="password", placeholder="Tạo mật khẩu an toàn", key="reg_pass")
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        if st.button("✨ Xác Nhận Đăng Ký", use_container_width=True):
            if new_user.strip() and new_pass.strip():
                if get_user(new_user.strip()):
                    st.error("⚠️ Tên tài khoản này đã tồn tại, vui lòng chọn tên khác!")
                else:
                    if create_user(new_user.strip(), 1000, 'user', new_pass.strip()):
                        st.success("✅ Đăng ký thành công! Bạn có thể chuyển sang trang đăng nhập để bắt đầu.")
                    else:
                        st.error("❌ Đăng ký thất bại, vui lòng thử lại sau.")
            else:
                st.warning("⚠️ Vui lòng điền đầy đủ thông tin đăng ký.")
        st.markdown('</div>', unsafe_allow_html=True)