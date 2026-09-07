# admin.py (Cập nhật giao diện biểu đồ thống kê trực quan và tối ưu)
import streamlit as st
import pandas as pd
from db import get_all_users, set_user_elo, get_connection, update_user_role, delete_user, update_user_status

def render_admin_page():
    st.markdown("""
        <style>
        .admin-header {
            background: linear-gradient(135deg, #5c3a21, #8d5b4c);
            padding: 30px;
            border-radius: 16px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 25px rgba(92, 58, 33, 0.2);
            margin-bottom: 25px;
        }
        .admin-header h1 {
            margin: 0;
            font-size: 30px;
            font-weight: 800;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .admin-header p {
            margin: 8px 0 0 0;
            font-size: 15px;
            opacity: 0.9;
        }
        .metric-container {
            background: linear-gradient(135deg, #ffffff, #fdfaf6);
            padding: 20px;
            border-radius: 14px;
            border: 1px solid #e6d7c3;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            text-align: center;
        }
        .admin-card {
            background: #ffffff;
            padding: 18px 22px;
            border-radius: 14px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.04);
            border: 1px solid #eedecc;
            margin-bottom: 12px;
        }
        .role-badge-admin {
            background-color: #ffe8d6; color: #b95c2d; padding: 3px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid #f3cbb0;
        }
        .role-badge-user {
            background-color: #eaf4f4; color: #2b7a78; padding: 3px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid #c6e2e2;
        }
        .status-active {
            background-color: #e1f5fe; color: #0277bd; padding: 3px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid #b3e5fc;
        }
        .status-locked {
            background-color: #ffebee; color: #c62828; padding: 3px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; border: 1px solid #ffcdd2;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="admin-header">
            <h1>👑 Bảng Điều Hành Quản Trị Hệ Thống</h1>
            <p>Kiểm soát trạng thái hoạt động, khóa/mở khóa tài khoản, phân quyền và tinh chỉnh Elo</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["👥 Quản lý Elo & Trạng Thái", "🛡️ Phân Quyền & Khóa/Mở Khóa", "📊 Thống Kê & Biểu Đồ"])

    users = get_all_users()

    with tab1:
        st.markdown("### 📋 Danh Sách Thành Viên & Chỉnh Sửa Elo")
        search_query = st.text_input("🔍 Tìm kiếm tên tài khoản", placeholder="Nhập tên đăng nhập cần tìm...")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        for u in users:
            if search_query and search_query.lower() not in u['username'].lower():
                continue

            status = u.get('status', 'active')
            
            with st.container():
                st.markdown('<div class="admin-card">', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns([2, 1.2, 1.5, 1.2])
                
                with col1:
                    st.markdown(f"<div style='font-size: 16px; font-weight: bold; color: #4a3525;'>👤 {u['username']}</div>", unsafe_allow_html=True)
                    role_class = "role-badge-admin" if u['role'] == 'admin' else "role-badge-user"
                    status_class = "status-active" if status == 'active' else "status-locked"
                    status_text = "🟢 Đang hoạt động" if status == 'active' else "🔴 Đã khóa"
                    
                    st.markdown(f"Quyền: <span class='{role_class}'>{u['role'].upper()}</span> | Trạng thái: <span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"<div style='margin-top: 5px; color: #665; font-size: 14px;'>Elo: <b>{u['elo']}</b></div>", unsafe_allow_html=True)
                
                with col3:
                    new_elo = st.number_input("Elo mới", value=int(u['elo']), key=f"elo_{u['username']}", label_visibility="collapsed")
                
                with col4:
                    if st.button("💾 Lưu Elo", key=f"btn_elo_{u['username']}", use_container_width=True):
                        set_user_elo(u['username'], int(new_elo))
                        st.success(f"Đã cập nhật Elo cho {u['username']}!")
                        st.rerun()
                        
                st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("### ⚙️ Quản Trị Phân Quyền & Trạng Thái Tài Khoản (Khóa/Mở)")
        st.info("💡 Bạn có thể khóa tài khoản vi phạm (người bị khóa sẽ không thể đăng nhập) hoặc phân lại quyền Admin/User tại đây.")

        for u in users:
            is_self = (u['username'] == st.session_state.get('current_user'))
            current_status = u.get('status', 'active')

            with st.expander(f"👤 Tài khoản: {u['username']} (Quyền: {u['role'].upper()} | Trạng thái: {'Đang hoạt động' if current_status == 'active' else 'Đã bị khóa'})"):
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.markdown("#### Đổi quyền hạn")
                    new_role_val = st.selectbox(
                        "Chọn quyền mới", 
                        options=["user", "admin"], 
                        index=0 if u['role'] == 'user' else 1,
                        key=f"select_role_{u['username']}"
                    )
                    if st.button("🔄 Cập nhật quyền", key=f"btn_role_{u['username']}"):
                        if is_self and new_role_val == 'user':
                            st.warning("⚠️ Không thể tự hạ quyền admin của chính mình!")
                        else:
                            update_user_role(u['username'], new_role_val)
                            st.success(f"Đã chuyển quyền của {u['username']} thành {new_role_val}!")
                            st.rerun()

                with col_b:
                    st.markdown("#### Trạng thái tài khoản")
                    if is_self:
                        st.info("🔒 Không thể khóa tài khoản chính bạn đang đăng nhập.")
                    else:
                        normalized_status = str(current_status).strip().lower()
                        if normalized_status == 'active':
                            if st.button("🔒 Khóa tài khoản", key=f"btn_lock_{u['username']}", type="secondary"):
                                update_user_status(u['username'], 'locked')
                                st.warning(f"Đã khóa tài khoản {u['username']} thành công!")
                                st.rerun()
                        else:
                            if st.button("🔓 Mở khóa tài khoản", key=f"btn_unlock_{u['username']}", type="primary"):
                                update_user_status(u['username'], 'active')
                                st.success(f"Đã mở khóa cho tài khoản {u['username']}!")
                                st.rerun()

                with col_c:
                    st.markdown("#### Xóa vĩnh viễn")
                    if is_self:
                        st.write("---")
                    else:
                        confirm_delete = st.checkbox("Xác nhận xóa", key=f"chk_del_{u['username']}")
                        if st.button("🗑️ Xóa vĩnh viễn", key=f"btn_del_{u['username']}"):
                            if confirm_delete:
                                delete_user(u['username'])
                                st.success(f"Đã xóa tài khoản {u['username']}!")
                                st.rerun()
                            else:
                                st.warning("Hãy tích chọn xác nhận trước.")

    with tab3:
        st.markdown("### 📈 Thống Kê & Phân Tích Hệ Thống")
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'locked'")
            total_locked = cursor.fetchone()[0]
        except:
            total_locked = 0
            
        total_active = total_users - total_locked

        cursor.execute("SELECT COUNT(*) FROM match_history")
        total_matches = cursor.fetchone()[0]
        
        conn.close()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
                <div class="metric-container">
                    <h5 style="color: #7f634d; margin: 0 0 5px 0;">Đang hoạt động</h5>
                    <h3 style="color: #2b7a78; margin: 0;">🟢 {total_active}</h3>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class="metric-container">
                    <h5 style="color: #7f634d; margin: 0 0 5px 0;">Đang bị khóa</h5>
                    <h3 style="color: #c62828; margin: 0;">🔴 {total_locked}</h3>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div class="metric-container">
                    <h5 style="color: #7f634d; margin: 0 0 5px 0;">Tổng ván đấu</h5>
                    <h3 style="color: #5c3a21; margin: 0;">🎮 {total_matches}</h3>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
                <div class="metric-container">
                    <h5 style="color: #7f634d; margin: 0 0 5px 0;">Tổng số user</h5>
                    <h3 style="color: #5c3a21; margin: 0;">👥 {total_users}</h3>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

        if users:
            df_users = pd.DataFrame(users)
            if 'status' not in df_users.columns:
                df_users['status'] = 'active'
                
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.markdown("#### 📊 Tỷ lệ trạng thái tài khoản")
                # Thay thế biểu đồ cột bị lỗi giao diện bằng bảng phân tích tỷ lệ và thanh tiến trình trực quan
                active_pct = (total_active / total_users) * 100 if total_users > 0 else 0
                locked_pct = (total_locked / total_users) * 100 if total_users > 0 else 0
                
                st.markdown(f"""
                    <div style="background: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #eedecc; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                        <p style="margin-bottom: 8px; font-weight: 600; color: #5c3a21;">🟢 Hoạt động: <b>{total_active} tài khoản</b> ({active_pct:.1f}%)</p>
                        <hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;">
                        <p style="margin-bottom: 8px; font-weight: 600; color: #c62828;">🔴 Bị khóa: <b>{total_locked} tài khoản</b> ({locked_pct:.1f}%)</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Vẽ biểu đồ ngang gọn gàng hơn cho trạng thái
                status_df = pd.DataFrame({
                    "Trạng thái": ["Đang hoạt động", "Đang bị khóa"],
                    "Số lượng": [total_active, total_locked]
                }).set_index("Trạng thái")
                st.bar_chart(status_df, color="#2b7a78", horizontal=True)

            with col_chart2:
                st.markdown("#### 📈 Phân bố điểm Elo người chơi")
                if 'username' in df_users.columns and 'elo' in df_users.columns:
                    chart_data = df_users.set_index('username')[['elo']]
                    st.bar_chart(chart_data, color="#8d5b4c")