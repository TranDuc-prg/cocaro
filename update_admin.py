import sqlite3

# Kết nối tới database caro.db
conn = sqlite3.connect('caro.db')
cursor = conn.cursor()

# Cập nhật tài khoản 'duc' lên thành admin (bạn có thể đổi chữ 'duc' thành tên tài khoản của bạn)
cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'duc'")

conn.commit()
conn.close()

print("Đã cấp quyền admin thành công!")