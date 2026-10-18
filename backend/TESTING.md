# Kiểm tra backend Python

Chạy tại thư mục backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test dùng database SQLite tạm riêng cho từng test, không truy cập MySQL hay broker
thật. MQTT publish được giả lập; xử lý bản tin dùng chính service của ứng dụng.

Phạm vi: 12 REST endpoint, login SHA-256, profile, định dạng envelope/camelCase,
phân trang, lọc thời gian bao gồm đơn vị cuối, dữ liệu DHT lỗi, ACK cập nhật cùng một
history, retained snapshot, publish lỗi, timeout, LED chưa map, đăng ký lại topic
khi reconnect, WebSocket event/filter và seed không ghi đè dữ liệu hiện có.

Kiểm tra thủ công với MySQL/Mosquitto/ESP32:

1. Cấu hình `.env`, khởi động MySQL và broker rồi chạy uvicorn theo README.
2. Kiểm tra `/docs`, `/api/devices`, `/api/sensors`. Đối chiếu MQTT_DEVICE_MAP với
   ID thật trong database và LED1/LED2 của mạch.
3. Nạp firmware, kiểm tra có dữ liệu mới qua `/api/sensors/latest` và `/api/sensors/data`.
4. Mở WebSocket `/ws`, gửi POST `/api/devices/control`; kiểm tra đèn vật lý,
   trạng thái thiết bị và đúng một history chuyển từ PENDING sang SUCCESS.
5. Ngắt mạch và gửi lệnh: history phải FAILED sau timeout. Ngắt broker: POST trả 503.
6. Khởi động broker lại: xác nhận service tự kết nối và nhận dữ liệu mới.
7. Khởi động backend lại: giữ dữ liệu; retained status không thêm history SUCCESS giả.

Các test tự động không chứng minh kết nối MySQL, cấu hình broker hay dây nối thực tế.

Kiểm thử bổ sung cho FE/BE: trạng thái kết nối và hết hạn heartbeat ESP32,
capability/pending của thiết bị, lọc loại cảm biến/giá trị, lọc hành động và sort
lịch sử trước phân trang. Frontend có `npm test` cho hợp đồng API, ACK, timeout và
reconnect. Đã kiểm tra API qua Vite proxy và nhận gói cảm biến thật qua `/ws`.
