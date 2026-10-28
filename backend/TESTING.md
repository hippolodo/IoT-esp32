# Kiểm tra backend Python

Chạy tại thư mục backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test dùng database SQLite tạm riêng cho từng test, không truy cập MySQL hay broker
thật. MQTT publish được giả lập; xử lý bản tin dùng chính service của ứng dụng.
`tests/db_setup.py` chuẩn bị bảng và dữ liệu mẫu cho DB SQLite tạm trước khi mở
TestClient; phần này không được ứng dụng import hay gọi khi chạy BE.

Phạm vi: 18 REST endpoint, đăng ký/PBKDF2 và login SHA-256 tương thích, profile, định dạng envelope/camelCase,
phân trang, lọc thời gian bao gồm đơn vị cuối, dữ liệu DHT lỗi, ACK cập nhật cùng một
history, retained snapshot, publish lỗi, timeout, LED chưa map, đăng ký lại topic
khi reconnect, WebSocket event/filter. Startup được kiểm tra không tạo bảng,
không bổ sung danh mục và không sửa dữ liệu có sẵn.
Các API GET dữ liệu được kiểm tra với token thiếu, giả, hết hạn và đã đăng xuất.
WebSocket kiểm tra xác thực bản tin đầu tiên/header, từ chối trước khi subscribe,
và đóng phiên đã hết hạn/thu hồi ngay cả khi không có sự kiện mới.
Kiểm tra thêm hai app chạy đồng thời phải giữ riêng DB, token và cấu hình MQTT.
Các service dùng SQL trực tiếp có tham số. Test kiểm tra dấu nháy không thay đổi
cấu trúc truy vấn, ký tự `%`/`_` trong tìm kiếm được xử lý như giá trị literal,
và đăng xuất chỉ xóa đúng phiên hiện tại.

Kiểm tra thủ công với MySQL/Mosquitto/ESP32:

1. Cấu hình `.env`, khởi động MySQL và broker rồi chạy uvicorn theo README.
2. Đăng nhập trong `/docs`, dán token vào Authorize rồi kiểm tra `/api/devices`, `/api/sensors`. Đối chiếu MQTT_DEVICE_MAP với
   ID thật trong database và LED1/LED2 của mạch.
3. Nạp firmware, kiểm tra có dữ liệu mới qua `/api/sensors/latest` và `/api/sensors/data`.
4. Mở WebSocket `/ws` và gửi bản tin xác thực theo README, gửi POST `/api/devices/control`; kiểm tra đèn vật lý,
   trạng thái thiết bị và đúng một history chuyển từ PENDING sang SUCCESS.
5. Ngắt mạch và gửi lệnh: history phải FAILED sau timeout. Ngắt broker: POST trả 503.
6. Khởi động broker lại: xác nhận service tự kết nối và nhận dữ liệu mới.
7. Khởi động backend lại: giữ dữ liệu, không tự tạo bảng/seed; retained status không thêm history SUCCESS giả.

Các test tự động không chứng minh kết nối MySQL, cấu hình broker hay dây nối thực tế.

Kiểm thử bổ sung cho FE/BE: trạng thái kết nối và hết hạn heartbeat ESP32,
capability/pending của thiết bị, lọc loại cảm biến/giá trị, lọc hành động và sort
lịch sử trước phân trang. Frontend có `npm test` cho hợp đồng API, ACK, timeout và
reconnect. Đã kiểm tra API qua Vite proxy và nhận gói cảm biến thật qua `/ws`.
