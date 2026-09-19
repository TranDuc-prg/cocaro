import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

from db import (
    get_all_users,
    set_user_elo,
    get_connection,
    update_user_role,
    delete_user,
    update_user_status,
)
from config import DB_PATH


def _ensure_admin_tables():
    """Create/migrate tables/columns used by the admin dashboard."""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                room_id TEXT,
                result TEXT,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cols = {row[1] for row in conn.execute("PRAGMA table_info(game_feedback)").fetchall()}
        if "admin_reply" not in cols:
            conn.execute("ALTER TABLE game_feedback ADD COLUMN admin_reply TEXT")
        if "status" not in cols:
            conn.execute("ALTER TABLE game_feedback ADD COLUMN status TEXT DEFAULT 'new'")
        if "replied_at" not in cols:
            conn.execute("ALTER TABLE game_feedback ADD COLUMN replied_at TEXT")

        conn.commit()
    finally:
        conn.close()


def _feedback_rows(where_sql="", params=()):
    _ensure_admin_tables()
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        query = """
            SELECT id, username, game_mode, room_id, result, rating,
                   comment, created_at, admin_reply, status, replied_at
            FROM game_feedback
        """
        if where_sql:
            query += " WHERE " + where_sql
        query += " ORDER BY id DESC"
        rows = conn.execute(query, params).fetchall()
        return rows
    finally:
        conn.close()


def _update_feedback(feedback_id, status=None, admin_reply=None):
    _ensure_admin_tables()
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        current = conn.execute(
            "SELECT status, admin_reply FROM game_feedback WHERE id = ?",
            (int(feedback_id),),
        ).fetchone()
        if not current:
            return False

        new_status = status if status is not None else current[0]
        new_reply = admin_reply if admin_reply is not None else current[1]
        replied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if admin_reply is not None else None

        conn.execute(
            """
            UPDATE game_feedback
            SET status = ?, admin_reply = ?,
                replied_at = CASE
                    WHEN ? IS NOT NULL THEN ?
                    ELSE replied_at
                END
            WHERE id = ?
            """,
            (new_status, new_reply, replied_at, replied_at, int(feedback_id)),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def _delete_feedback(feedback_id):
    _ensure_admin_tables()
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        conn.execute("DELETE FROM game_feedback WHERE id = ?", (int(feedback_id),))
        conn.commit()
    finally:
        conn.close()


def _match_rows(player_filter="", result_filter="Tất cả", limit=300):
    conn = get_connection()
    try:
        query = """
            SELECT id, player, opponent, result, score, timestamp
            FROM match_history
            WHERE 1=1
        """
        params = []
        if player_filter.strip():
            query += " AND (player LIKE ? OR opponent LIKE ?)"
            token = f"%{player_filter.strip()}%"
            params.extend([token, token])
        if result_filter != "Tất cả":
            query += " AND result = ?"
            params.append(result_filter)
        query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(int(limit))
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def _delete_match(match_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM match_history WHERE id = ?", (int(match_id),))
        conn.commit()
    finally:
        conn.close()


def _delete_all_matches():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM match_history")
        conn.commit()
    finally:
        conn.close()


def _room_rows():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT room_id, size, turn, winner, players,
                   game_ended, move_history
            FROM rooms
            ORDER BY room_id ASC
            """
        ).fetchall()
        return rows
    finally:
        conn.close()


def _delete_room(room_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
        conn.commit()
    finally:
        conn.close()


def _system_overview(users):
    conn = get_connection()
    try:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        locked_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE COALESCE(status, 'active') = 'locked'"
        ).fetchone()[0]
        total_matches = conn.execute("SELECT COUNT(*) FROM match_history").fetchone()[0]
        total_rooms = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        finished_rooms = conn.execute("SELECT COUNT(*) FROM rooms WHERE game_ended = 1").fetchone()[0]
        return total_users, locked_users, total_matches, total_rooms, finished_rooms
    finally:
        conn.close()


def render_admin_page():
    _ensure_admin_tables()

    st.markdown(
        """
        <style>
        .admin-header {
            background: linear-gradient(135deg, #4e2f1d, #8b5e3c);
            padding: 28px;
            border-radius: 16px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 25px rgba(78, 47, 29, 0.20);
            margin-bottom: 20px;
        }
        .admin-header h1 { margin: 0; font-size: 30px; font-weight: 800; }
        .admin-header p { margin: 8px 0 0 0; font-size: 14px; opacity: .92; }
        .metric-card {
            background: linear-gradient(135deg, #ffffff, #fdf8f2);
            padding: 18px;
            border-radius: 14px;
            border: 1px solid #eadac7;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            text-align: center;
        }
        .section-title { font-size: 20px; font-weight: 800; margin: 8px 0 14px 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="admin-header">
            <h1>👑 BẢNG ĐIỀU HÀNH QUẢN TRỊ</h1>
            <p>Quản lý người dùng, Elo, phòng đấu, lịch sử trận, đánh giá và thống kê hệ thống</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    users = get_all_users()
    total_users, locked_users, total_matches, total_rooms, finished_rooms = _system_overview(users)

    feedback_all = _feedback_rows()
    feedback_ratings = [int(r[5]) for r in feedback_all]
    avg_rating = sum(feedback_ratings) / len(feedback_ratings) if feedback_ratings else 0

    st.markdown("### 📌 Tổng quan hệ thống")
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, "👥 Người dùng", total_users),
        (c2, "🔒 Tài khoản khóa", locked_users),
        (c3, "🎮 Tổng trận", total_matches),
        (c4, "🏠 Phòng hiện có", total_rooms),
        (c5, "⭐ Đánh giá TB", f"{avg_rating:.1f}/5" if feedback_ratings else "Chưa có"),
    ]
    for col, label, value in metrics:
        with col:
            st.markdown(
                f"<div class='metric-card'><div style='font-size:13px;color:#7c6755'>{label}</div>"
                f"<div style='font-size:26px;font-weight:800;color:#4e2f1d;margin-top:6px'>{value}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    tabs = st.tabs([
        "📊 Dashboard",
        "👥 Người dùng",
        "⭐ Quản lý đánh giá",
        "📜 Lịch sử trận",
        "🏠 Quản lý phòng",
        "🏆 Elo & Thống kê",
    ])

    with tabs[0]:
        st.markdown("<div class='section-title'>📊 Dashboard quản trị</div>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Trạng thái tài khoản")
            active = max(0, total_users - locked_users)
            status_df = pd.DataFrame(
                {"Số lượng": [active, locked_users]},
                index=["Đang hoạt động", "Đã khóa"],
            )
            st.bar_chart(status_df)

        with col_b:
            st.markdown("#### Phân bố đánh giá")
            rating_counts = {star: 0 for star in range(1, 6)}
            for rating in feedback_ratings:
                rating_counts[rating] += 1
            rating_df = pd.DataFrame(
                {"Số lượt": list(rating_counts.values())},
                index=[f"{s} sao" for s in range(1, 6)],
            )
            st.bar_chart(rating_df)

        st.markdown("#### 🕹️ Tình trạng phòng Online")
        rooms = _room_rows()
        if rooms:
            room_stats = []
            for room_id, size, turn, winner, players_json, game_ended, move_history_json in rooms:
                player_count = 0
                move_count = 0
                try:
                    import json
                    player_count = len(json.loads(players_json or "{}"))
                    move_count = len(json.loads(move_history_json or "[]"))
                except Exception:
                    pass
                room_stats.append(
                    {
                        "Phòng": room_id,
                        "Bàn": f"{size}x{size}",
                        "Người chơi": player_count,
                        "Nước đi": move_count,
                        "Lượt": turn,
                        "Trạng thái": "Đã kết thúc" if game_ended else "Đang chơi",
                        "Kết quả": winner or "-",
                    }
                )
            st.dataframe(pd.DataFrame(room_stats), use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có phòng Online.")

        st.markdown("#### 🕐 Hoạt động gần đây")
        matches = _match_rows(limit=10)
        if matches:
            df = pd.DataFrame(
                matches,
                columns=["ID", "Người chơi", "Đối thủ", "Kết quả", "Điểm", "Thời gian"],
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có lịch sử trận đấu.")

        st.markdown("#### 💾 Sao lưu dữ liệu")
        try:
            with open(DB_PATH, "rb") as db_file:
                db_bytes = db_file.read()
            st.download_button(
                "📥 Tải xuống caro.db",
                data=db_bytes,
                file_name="caro_backup.db",
                mime="application/x-sqlite3",
                use_container_width=True,
            )
            st.caption("Bản sao lưu chứa người dùng, Elo, lịch sử trận, phòng và đánh giá.")
        except OSError as exc:
            st.warning(f"Không thể tạo bản sao lưu: {exc}")

    with tabs[1]:
        st.markdown("<div class='section-title'>👥 Quản lý người dùng</div>", unsafe_allow_html=True)
        search_query = st.text_input("🔍 Tìm tài khoản", placeholder="Nhập username...", key="admin_user_search")
        filtered_users = [u for u in users if not search_query or search_query.lower() in u["username"].lower()]

        for u in filtered_users:
            username = u["username"]
            status = u.get("status", "active")
            is_self = username == st.session_state.get("current_user")

            with st.expander(
                f"👤 {username} | Elo {u['elo']} | {u['role'].upper()} | "
                f"{'🟢 Active' if status == 'active' else '🔴 Locked'}"
            ):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    new_elo = st.number_input(
                        "Elo",
                        min_value=0,
                        value=int(u["elo"]),
                        step=10,
                        key=f"admin_elo_{username}",
                    )
                    if st.button("💾 Lưu Elo", key=f"save_elo_{username}", use_container_width=True):
                        set_user_elo(username, int(new_elo))
                        st.success(f"Đã cập nhật Elo cho {username}.")
                        st.rerun()

                with c2:
                    role = st.selectbox(
                        "Quyền",
                        ["user", "admin"],
                        index=0 if u["role"] == "user" else 1,
                        key=f"role_{username}",
                    )
                    if st.button("🔄 Cập nhật quyền", key=f"save_role_{username}", use_container_width=True):
                        if is_self and role == "user":
                            st.warning("Không thể tự hạ quyền tài khoản admin đang đăng nhập.")
                        else:
                            update_user_role(username, role)
                            st.success(f"Đã cập nhật quyền {username} → {role}.")
                            st.rerun()

                with c3:
                    if status == "active":
                        if is_self:
                            st.info("Không thể tự khóa tài khoản hiện tại.")
                        elif st.button("🔒 Khóa", key=f"lock_{username}", use_container_width=True):
                            update_user_status(username, "locked")
                            st.success(f"Đã khóa {username}.")
                            st.rerun()
                    else:
                        if st.button("🔓 Mở khóa", key=f"unlock_{username}", use_container_width=True, type="primary"):
                            update_user_status(username, "active")
                            st.success(f"Đã mở khóa {username}.")
                            st.rerun()

                with c4:
                    if is_self:
                        st.caption("Tài khoản hiện tại")
                    else:
                        confirm = st.checkbox("Xác nhận xóa", key=f"confirm_del_{username}")
                        if st.button("🗑️ Xóa", key=f"delete_{username}", use_container_width=True):
                            if confirm:
                                delete_user(username)
                                st.success(f"Đã xóa {username}.")
                                st.rerun()
                            else:
                                st.warning("Hãy xác nhận xóa trước.")

        st.markdown("#### 📈 Thống kê từng người chơi")
        user_stats = []
        conn = get_connection()
        try:
            for u in users:
                row = conn.execute(
                    """
                    SELECT
                        SUM(CASE WHEN result IN ('Thắng', 'Thắng (Quá giờ)') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN result LIKE 'Thua%' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN result = 'Hòa' THEN 1 ELSE 0 END),
                        COUNT(*)
                    FROM match_history
                    WHERE player = ?
                    """,
                    (u["username"],),
                ).fetchone()
                wins = int(row[0] or 0)
                losses = int(row[1] or 0)
                draws = int(row[2] or 0)
                total = int(row[3] or 0)
                user_stats.append(
                    {
                        "Username": u["username"],
                        "Elo": u["elo"],
                        "Tổng trận": total,
                        "Thắng": wins,
                        "Thua": losses,
                        "Hòa": draws,
                        "Tỷ lệ thắng": f"{(wins / total * 100):.1f}%" if total else "0.0%",
                    }
                )
        finally:
            conn.close()
        user_stats_df = pd.DataFrame(user_stats)
        st.dataframe(user_stats_df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Xuất thống kê người chơi CSV",
            data=user_stats_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="player_statistics.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tabs[2]:
        st.markdown("<div class='section-title'>⭐ Quản lý đánh giá người chơi</div>", unsafe_allow_html=True)

        ratings = [1, 2, 3, 4, 5]
        status_values = ["Tất cả", "new", "reviewed", "hidden"]
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            rating_filter = st.selectbox("Lọc số sao", ["Tất cả", *ratings], key="feedback_rating_filter")
        with fc2:
            status_filter = st.selectbox("Lọc trạng thái", status_values, key="feedback_status_filter")
        with fc3:
            feedback_search = st.text_input("🔍 Tìm username / nhận xét", key="feedback_search")

        clauses = []
        params = []
        if rating_filter != "Tất cả":
            clauses.append("rating = ?")
            params.append(int(rating_filter))
        if status_filter != "Tất cả":
            clauses.append("status = ?")
            params.append(status_filter)
        if feedback_search.strip():
            clauses.append("(username LIKE ? OR comment LIKE ? OR admin_reply LIKE ?)")
            token = f"%{feedback_search.strip()}%"
            params.extend([token, token, token])

        feedback_rows = _feedback_rows(" AND ".join(clauses), tuple(params))

        total_fb = len(feedback_all)
        avg_fb = sum(int(x[5]) for x in feedback_all) / total_fb if total_fb else 0
        five = sum(1 for x in feedback_all if int(x[5]) == 5)
        four = sum(1 for x in feedback_all if int(x[5]) == 4)
        low = sum(1 for x in feedback_all if int(x[5]) <= 2)
        new_fb = sum(1 for x in feedback_all if (x[9] or 'new') == 'new')
        reviewed_fb = sum(1 for x in feedback_all if (x[9] or 'new') == 'reviewed')
        hidden_fb = sum(1 for x in feedback_all if (x[9] or 'new') == 'hidden')

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Tổng đánh giá", total_fb)
        m2.metric("Điểm TB", f"{avg_fb:.2f}/5" if total_fb else "0/5")
        m3.metric("5 ⭐", five)
        m4.metric("≤ 2 ⭐", low)
        m5.metric("🆕 Chờ xử lý", new_fb)

        st.caption(f"Đã xem: {reviewed_fb} · Đã ẩn: {hidden_fb}")
        st.markdown("---")
        if not feedback_rows:
            st.info("Không có đánh giá phù hợp bộ lọc.")
        else:
            for row in feedback_rows:
                fid, username, game_mode, room_id, result, rating, comment, created_at, admin_reply, status, replied_at = row
                title = f"#{fid} | {username} | {'⭐' * int(rating)} | {status}"
                with st.expander(title):
                    a, b, c = st.columns([1.2, 1.2, 1])
                    a.write(f"**Chế độ:** {game_mode}")
                    b.write(f"**Kết quả:** {result or '-'}")
                    c.write(f"**Phòng:** {room_id or '-'}")
                    st.caption(f"Gửi lúc: {created_at}")

                    st.markdown("**📝 Nhận xét của User**")
                    st.write(comment or "(Không có nhận xét)")

                    current_status = st.selectbox(
                        "Trạng thái đánh giá",
                        ["new", "reviewed", "hidden"],
                        index=["new", "reviewed", "hidden"].index(status if status in {"new", "reviewed", "hidden"} else "new"),
                        key=f"feedback_status_{fid}",
                    )
                    reply = st.text_area(
                        "💬 Phản hồi của Admin",
                        value=admin_reply or "",
                        max_chars=500,
                        key=f"feedback_reply_{fid}",
                        placeholder="Ví dụ: Cảm ơn bạn đã góp ý. Chúng tôi sẽ cải thiện trải nghiệm...",
                    )
                    save_reply_col, hide_col, delete_col = st.columns(3)
                    with save_reply_col:
                        if st.button("💾 Lưu phản hồi", key=f"fb_save_{fid}", use_container_width=True, type="primary"):
                            _update_feedback(fid, status=current_status, admin_reply=reply.strip())
                            st.success("Đã cập nhật đánh giá.")
                            st.rerun()
                    with hide_col:
                        if st.button("🙈 Ẩn đánh giá", key=f"fb_hide_{fid}", use_container_width=True):
                            _update_feedback(fid, status="hidden")
                            st.success("Đã ẩn đánh giá.")
                            st.rerun()
                    with delete_col:
                        if st.button("🗑️ Xóa đánh giá", key=f"fb_delete_{fid}", use_container_width=True):
                            _delete_feedback(fid)
                            st.success("Đã xóa đánh giá.")
                            st.rerun()

            st.download_button(
                "📥 Xuất danh sách đánh giá CSV",
                data=pd.DataFrame(
                    feedback_rows,
                    columns=[
                        "ID", "Username", "Chế độ", "Phòng", "Kết quả", "Rating",
                        "Comment", "Created At", "Admin Reply", "Status", "Replied At"
                    ],
                ).to_csv(index=False).encode("utf-8-sig"),
                file_name="feedback_export.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with tabs[3]:
        st.markdown("<div class='section-title'>📜 Quản lý lịch sử trận đấu</div>", unsafe_allow_html=True)
        mc1, mc2 = st.columns(2)
        with mc1:
            player_filter = st.text_input("🔍 Tìm người chơi / đối thủ", key="match_player_filter")
        with mc2:
            result_filter = st.selectbox(
                "Kết quả",
                ["Tất cả", "Thắng", "Thua", "Hòa", "Thắng (Quá giờ)"],
                key="match_result_filter",
            )

        match_rows = _match_rows(player_filter, result_filter, limit=500)
        if match_rows:
            df_match = pd.DataFrame(
                match_rows,
                columns=["ID", "Người chơi", "Đối thủ", "Kết quả", "Điểm", "Thời gian"],
            )
            st.dataframe(df_match, use_container_width=True, hide_index=True)

            delete_id = st.number_input("ID trận cần xóa", min_value=0, step=1, value=0, key="match_delete_id")
            d1, d2 = st.columns(2)
            with d1:
                if st.button("🗑️ Xóa trận theo ID", use_container_width=True):
                    if delete_id > 0:
                        _delete_match(delete_id)
                        st.success(f"Đã xóa trận #{int(delete_id)}.")
                        st.rerun()
                    else:
                        st.warning("Nhập ID hợp lệ.")
            with d2:
                confirm_clear = st.checkbox("Tôi hiểu thao tác này xóa toàn bộ lịch sử", key="confirm_clear_matches")
                if st.button("⚠️ Xóa toàn bộ lịch sử", use_container_width=True):
                    if confirm_clear:
                        _delete_all_matches()
                        st.success("Đã xóa toàn bộ lịch sử trận đấu.")
                        st.rerun()
                    else:
                        st.warning("Hãy xác nhận trước khi xóa toàn bộ.")

            st.download_button(
                "📥 Xuất lịch sử trận đấu CSV",
                data=df_match.to_csv(index=False).encode("utf-8-sig"),
                file_name="match_history_export.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Không có lịch sử trận đấu phù hợp.")

    with tabs[4]:
        st.markdown("<div class='section-title'>🏠 Quản lý phòng Online</div>", unsafe_allow_html=True)
        rooms = _room_rows()
        if not rooms:
            st.info("Không có phòng nào trong hệ thống.")
        else:
            import json

            room_table = []
            for room_id, size, turn, winner, players_json, game_ended, move_history_json in rooms:
                try:
                    players = json.loads(players_json or "{}")
                    move_history = json.loads(move_history_json or "[]")
                except Exception:
                    players, move_history = {}, []
                room_table.append(
                    {
                        "Phòng": room_id,
                        "Bàn cờ": f"{size}x{size}",
                        "Người chơi": ", ".join(players.keys()) if players else "-",
                        "Số người": len(players),
                        "Số nước": len(move_history),
                        "Lượt": turn,
                        "Trạng thái": "Kết thúc" if game_ended else "Đang chơi",
                        "Người thắng": winner or "-",
                    }
                )

            st.dataframe(pd.DataFrame(room_table), use_container_width=True, hide_index=True)
            st.markdown("#### 🧹 Dọn phòng")
            room_ids = [r["Phòng"] for r in room_table]
            selected_room = st.selectbox("Chọn phòng", room_ids, key="admin_room_select")
            confirm_room_delete = st.checkbox("Xác nhận xóa phòng này", key="admin_room_confirm")
            if st.button("🗑️ Xóa phòng", use_container_width=True):
                if confirm_room_delete:
                    _delete_room(selected_room)
                    st.success(f"Đã xóa phòng {selected_room}.")
                    st.rerun()
                else:
                    st.warning("Hãy xác nhận trước khi xóa phòng.")
    with tabs[5]:
        st.markdown("<div class='section-title'>🏆 Elo & Thống kê người chơi</div>", unsafe_allow_html=True)
        top_n = st.radio("Hiển thị", [10, 20], horizontal=True, index=0, key="leaderboard_top_n")
        leaderboard = sorted(users, key=lambda x: (-int(x["elo"]), x["username"]))[:top_n]

        rows = []
        conn = get_connection()
        try:
            for idx, u in enumerate(leaderboard, 1):
                stats = conn.execute(
                    """
                    SELECT
                        COUNT(*),
                        SUM(CASE WHEN result IN ('Thắng', 'Thắng (Quá giờ)') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN result LIKE 'Thua%' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN result = 'Hòa' THEN 1 ELSE 0 END)
                    FROM match_history
                    WHERE player = ?
                    """,
                    (u["username"],),
                ).fetchone()
                total = int(stats[0] or 0)
                wins = int(stats[1] or 0)
                losses = int(stats[2] or 0)
                draws = int(stats[3] or 0)
                rows.append(
                    {
                        "Hạng": idx,
                        "Người chơi": u["username"],
                        "Elo": u["elo"],
                        "Trận": total,
                        "Thắng": wins,
                        "Thua": losses,
                        "Hòa": draws,
                        "Tỷ lệ thắng": f"{(wins / total * 100):.1f}%" if total else "0.0%",
                    }
                )
        finally:
            conn.close()

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có người chơi.")

        st.markdown("#### 📈 Elo hiện tại")
        if users:
            elo_df = pd.DataFrame(
                {"Elo": [u["elo"] for u in sorted(users, key=lambda x: x["elo"], reverse=True)[:top_n]]},
                index=[u["username"] for u in sorted(users, key=lambda x: x["elo"], reverse=True)[:top_n]],
            )
            st.bar_chart(elo_df)
