# CoCaRo - Core files fixed

Đã sửa các file lõi để Online lưu và thống kê lịch sử nước đi ổn định qua Streamlit rerun.

## File lõi
- `db.py`: migration SQLite + lưu/đọc `last_move`, `move_history`, `turn_start_time`; dùng UPSERT thay cho INSERT OR REPLACE.
- `game_logic.py`: `apply_move()` kiểm tra dữ liệu, ghi lịch sử và lưu thời gian lượt ngay khi đánh.
- `room_manager.py`: khởi tạo phòng với đầy đủ trạng thái persistent.
- `elo.py`: chống cập nhật ELO/lịch sử trận đấu 2 lần khi có 2 trình duyệt cùng nhận kết quả.
- `app.py`: đồng bộ Online từ SQLite, lấy thống kê sau khi ELO cập nhật, reset ván mới đúng cách và không bắn balloons mỗi giây.

## Chạy
```bash
pip install -r requirements.txt
streamlit run app.py
```

Database cũ `caro.db` sẽ được migration tự động khi `init_db()` chạy. Các nước đi của những ván cũ không thể khôi phục nếu trước đây chúng chưa được lưu.
