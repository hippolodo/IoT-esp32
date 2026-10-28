# Cấu trúc backend

Backend giữ nguyên 18 REST API, WebSocket `/ws`, định dạng JSON và tên bảng DB.
Điểm chạy vẫn là `app.main:app`; frontend không cần thay URL.

```text
app/
├── main.py                  # Tạo app, middleware, startup/shutdown, gắn router
├── config.py                # Đọc .env: database, MQTT, CORS
├── database.py              # Engine và session factory
├── dependencies.py          # DB, người đăng nhập, MQTT, cấu hình của từng app
├── contracts.py             # Envelope, serializer, phân trang, thời gian Việt Nam
├── schemas.py               # LoginRequest, RegisterRequest, DeviceControlRequest
├── passwords.py             # Băm và kiểm tra mật khẩu
├── models/
│   └── __init__.py          # Các model SQLAlchemy và quan hệ giữa bảng
├── routers/
│   ├── auth.py              # Đăng ký, đăng nhập, đăng xuất, hồ sơ
│   ├── devices.py           # Danh sách, chi tiết, điều khiển đèn
│   ├── sensors.py           # Danh mục, số đo, lịch sử biểu đồ, lọc
│   ├── history.py           # Lịch sử điều khiển/cảnh báo
│   ├── alerts.py            # Thống kê tháng và cảnh báo từng ngày
│   ├── system.py            # Health và trạng thái kết nối
│   └── realtime.py          # Xác thực và truyền sự kiện WebSocket
└── services/
    ├── auth.py              # Tài khoản, cấp token, kiểm tra phiên
    ├── devices.py           # Truy vấn thiết bị, chuyển yêu cầu điều khiển
    ├── sensors.py           # Truy vấn và ghép dữ liệu cảm biến/biểu đồ
    ├── history.py           # Lọc, sắp xếp, phân trang lịch sử
    ├── alerts.py            # Truy vấn thống kê cảnh báo gió
    └── mqtt.py              # MQTT, ACK, timeout, lưu số đo/cảnh báo, EventHub
```

## Trách nhiệm từng lớp

- **Router** khai báo method/URL, schema đầu vào, xác thực, rồi gọi service.
  Kết quả được đóng gói bằng `envelope()` tại router.
- **Service** xử lý nghiệp vụ, kiểm tra điều kiện và truy vấn dữ liệu. Service
  viết SQL trực tiếp (`SELECT/INSERT/UPDATE/DELETE`), truyền giá trị bằng tham số
  và trả dữ liệu kết quả; không khai báo endpoint hay phụ thuộc `Request`.
- **Model** mô tả cấu trúc bảng và phục vụ fixture kiểm thử. Nghiệp vụ không dùng
  ORM `db.add()`, `db.get()` hoặc tự sinh query từ model nữa.
- **Dependency** lấy DB/MQTT/cấu hình từ `request.app.state`, tránh dùng nhầm
  kết nối hoặc phiên khi tạo nhiều app trong kiểm thử.
- **Database có sẵn**: BE không tự tạo bảng, sửa schema hay seed lúc startup.
  Khi cần thay đổi cấu trúc DB, chạy SQL/migration riêng.

## Ví dụ lần theo code

Điều khiển đèn:

```text
routers/devices.py: control()
  → schemas.py: DeviceControlRequest
  → dependencies.py: current_user(), get_mqtt()
  → services/devices.py: control()
  → services/mqtt.py: MqttService.control()
  → ESP32 → MqttService._device_status()
  → SQL UPDATE devices/histories → EventHub → WebSocket
```

Lấy dữ liệu biểu đồ Dashboard:

```text
routers/sensors.py: sensor_chart()
  → dependencies.py: database(), current_session()
  → services/sensors.py: sensor_chart()
  → SQL SELECT datasensors JOIN sensors
  → router bọc envelope → frontend
```

## Các vị trí đã chuyển

| Trước đây | Hiện tại |
|---|---|
| API và truy vấn tập trung trong `main.py` | `routers/` và `services/` theo chức năng |
| Model trong `database.py` | `models/__init__.py` |
| Tự khởi tạo/seed khi startup | Đã bỏ; dùng database có sẵn |
| `app/mqtt.py` | `app/services/mqtt.py` |
| API hồ sơ trong `routers/users.py` | Gộp vào `routers/auth.py` |
| Mật khẩu trong `security/` | Gộp về `app/passwords.py` |
| Request model trong `main.py` và `schemas/` | Gộp vào `schemas.py` |
| Hàm xác thực phụ thuộc closure của `create_app` | `dependencies.py`, `services/auth.py` |
| WebSocket trong `main.py` | `routers/realtime.py` |

Lệnh chạy từ thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8088
```

Nên dừng và khởi động lại BE một lần sau khi thay đổi cấu trúc module.

## Thứ tự đọc code

Đọc `config.py` → `models/__init__.py` → `database.py` →
`schemas.py` → `dependencies.py` → `routers/` → service tương ứng.
Sau đó đọc `main.py` để thấy các phần được nối lại khi app khởi động.
Các tiện ích dùng chung, `ControlError` và xử lý lỗi HTTP nằm ở `contracts.py`.
`execute_sql()` trong file này gọi `db.execute(text(sql), params)` và gắn kiểu
datetime cho tham số để MySQL/SQLite xử lý thời gian nhất quán.

## Ví dụ SQL lưu lệnh điều khiển

Trong `services/mqtt.py`, `MqttService.control()` ghi:

```python
result = execute_sql(db, """
    INSERT INTO histories (device_id, user_id, action, status, timestamp)
    VALUES (:device_id, :user_id, :action, 'PENDING', :timestamp)
""", {'device_id': device_id, 'user_id': user_id, 'action': action, 'timestamp': now()})
history_id = result.lastrowid
```

SQL được thực thi ngay; `lastrowid` lấy ID mới. Giao dịch commit khi thoát
`with self.sessions.begin()`; sau đó mới publish MQTT. Khi ESP32 phản hồi,
`_device_status()` chạy `UPDATE devices ...` và `UPDATE histories ...`.
Không ghép giá trị người dùng vào câu SQL; các placeholder `:device_id` được bind.
Riêng từ khóa sắp xếp ASC/DESC được kiểm tra danh sách cho phép trước khi ghép.

Đợt tách cấu trúc đã đối chiếu OpenAPI trước/sau (không đổi), định nghĩa bảng
MySQL/SQLite (không đổi) và các truy vấn chỉ đọc trên MySQL hiện tại chạy được.
Sau khi bỏ startup seed/migration, fixture DB nằm riêng trong `tests/db_setup.py`;
test kiểm tra startup không tạo bảng hay bổ sung dữ liệu. MQTT được giả lập; hoạt động trên
mạch thật vẫn cần xác nhận khi chạy hệ thống với ESP32.
