@echo off
echo Dung MySQL...
net stop MySQL
timeout /t 2
echo Xoa du lieu cu (backup se duoc luu trong data_backup)...
move data data_backup
mkdir data
echo Khoi dong MySQL...
net start MySQL
echo Hoan tat. Hay tao database 'caro_db' trong phpMyAdmin.
pause