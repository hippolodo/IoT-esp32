# IoT backend — FastAPI

Python backend thay thế Spring Boot, chạy trên cổng **8088**. Dùng SQLAlchemy/MySQL,
Paho MQTT 2 và WebSocket thường. Frontend Vue đã nối REST/WebSocket qua Vite proxy
đến cổng 8088; dashboard nhận cảm biến, điều khiển đèn và đồng bộ trạng thái thật.

Backend được chia thành `routers/`, `services/`, `models/`, cùng `schemas.py`
và `passwords.py`. Xem [bản đồ file và luồng xử lý](#cấu-trúc-backend) để đọc code.
`main.py` quản lý khởi tạo/lifecycle và gắn router; các endpoint nằm trong `routers/`.
Các service dùng SQL trực tiếp có tham số qua `execute_sql()` trong `contracts.py`.
SQLAlchemy quản lý kết nối/transaction; model được giữ để mô tả bảng và phục vụ kiểm thử.

## Cấu trúc backend

Backend cung cấp REST API, WebSocket `/ws` và dữ liệu JSON cho hệ thống 3 cảm biến, 3 đèn.
Điểm chạy vẫn là `app.main:app`; frontend không cần thay URL.

```text
app/
├── main.py                  # Tạo app, middleware, startup/shutdown, gắn router
├── config.py                # Đọc .env: database, MQTT, CORS
├── database.py              # Engine và session factory
├── dependencies.py          # DB, người đăng nhập, MQTT, cấu hình của từng app
├── contracts.py             # Envelope, serializer, phân trang, thời gian Việt Nam
├── schemas.py               # Schema tài khoản, điều khiển đèn và ThresholdRequest
├── passwords.py             # Băm và kiểm tra mật khẩu
├── models/
│   └── __init__.py          # Các model SQLAlchemy và quan hệ giữa bảng
├── routers/
│   ├── auth.py              # Đăng ký, đăng nhập, đăng xuất, hồ sơ
│   ├── devices.py           # Danh sách, chi tiết, điều khiển đèn
│   ├── sensors.py           # Danh mục, số đo, lịch sử biểu đồ, lọc
│   ├── history.py           # Lịch sử điều khiển đèn
│   ├── thresholds.py        # Đọc, cấu hình và xác nhận 3 ngưỡng
│   ├── system.py            # Health và trạng thái kết nối
│   └── realtime.py          # Xác thực và truyền sự kiện WebSocket
└── services/
    ├── auth.py              # Tài khoản, cấp token, kiểm tra phiên
    ├── devices.py           # Truy vấn thiết bị, chuyển yêu cầu điều khiển
    ├── sensors.py           # Truy vấn và ghép dữ liệu cảm biến/biểu đồ
    ├── history.py           # Lọc, sắp xếp, phân trang lịch sử
    └── mqtt.py              # MQTT, ACK, timeout, lưu số đo, xác nhận ngưỡng, EventHub
```

### Trách nhiệm từng lớp

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

### Ví dụ lần theo code

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

### Các vị trí đã chuyển

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

### Thứ tự đọc code

Đọc `config.py` → `models/__init__.py` → `database.py` →
`schemas.py` → `dependencies.py` → `routers/` → service tương ứng.
Sau đó đọc `main.py` để thấy các phần được nối lại khi app khởi động.
Các tiện ích dùng chung, `ControlError` và xử lý lỗi HTTP nằm ở `contracts.py`.
`execute_sql()` trong file này gọi `db.execute(text(sql), params)` và gắn kiểu
datetime cho tham số để MySQL/SQLite xử lý thời gian nhất quán.

### Ví dụ SQL lưu lệnh điều khiển

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

## Chạy trên Windows PowerShell

Yêu cầu Python 3.11 trở lên, MySQL và Mosquitto (khi kết nối mạch).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Sửa `.env`: thông tin MySQL, MQTT username/password và ánh xạ thiết bị.
Nếu mật khẩu database có ký tự đặc biệt, URL-encode phần mật khẩu trong DATABASE_URL.
Tạo database nếu chưa có bằng MySQL client:

```sql
CREATE DATABASE IF NOT EXISTS iot_db CHARACTER SET utf8mb4;
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8088
```

- API docs: http://localhost:8088/docs
- Health: http://localhost:8088/api/auth/health
- Dừng backend Java trước khi chạy để tránh trùng cổng.
- Chạy **một worker**: MQTT callback, command lock và WebSocket hub cùng một process.
- Đặt `MQTT_ENABLED=false` để dùng REST/database khi chưa có broker.
- Broker mất kết nối không chặn khởi động REST; Paho thử kết nối lại và subscribe lại.
- CORS mặc định cho Vue ở localhost/127.0.0.1:5173; sửa `CORS_ORIGINS` nếu khác cổng.

## Database cũ

BE dùng database đã chuẩn bị sẵn: `users`, `devices`, `sensors`, `datasensors`,
`histories`, `auth_sessions`, `alert_counts`, `alert_history_details`, với đầy đủ cột theo `app/models/`.
Startup không tạo bảng, không sửa schema và không thêm dữ liệu mặc định.
Nếu thay đổi cấu trúc database, thực hiện riêng bằng SQL/migration trước khi chạy BE.
Dữ liệu hiện có được giữ nguyên; các API/MQTT tiếp tục đọc và ghi theo nghiệp vụ.

BE không tự tạo tài khoản mặc định. Dùng tài khoản đang có hoặc tạo tài khoản bằng
nút **Chưa có tài khoản? Đăng ký** trên FE hoặc `POST /api/auth/register`.
Tài khoản mới dùng PBKDF2-SHA256 (600.000 vòng, salt ngẫu nhiên); đăng nhập vẫn
đọc SHA-256 để tương thích tài khoản Java/seed cũ. Đăng nhập trả `accessToken` có hiệu lực 24 giờ;
frontend giữ token trong `sessionStorage` và gửi header `Authorization: Bearer <accessToken>`.
Tất cả REST API nghiệp vụ yêu cầu token hợp lệ, gồm cả GET thiết bị, cảm biến,
lịch sử và trạng thái hệ thống. Chỉ `/api/auth/health`, `/api/auth/register` và
`/api/auth/login` công khai. Hồ sơ trả đúng người đăng nhập, không trả `passwordHash`.
Đăng xuất thu hồi token phía backend.
Backend lấy người thực hiện từ phiên đăng nhập, không nhận `userId` do FE tự khai báo.
API lịch sử trả thêm `userId`; các bản ghi cũ trả null.

Đăng ký không yêu cầu token, nhận JSON:

```json
{
  "username": "new_user",
  "fullName": "Nguyễn Văn Hiệp",
  "email": "hiep@example.com",
  "password": "example-password-123",
  "confirmPassword": "example-password-123"
}
```

Tên đăng nhập gồm 3–50 ký tự chữ ASCII, số, `.`, `_`, `-`; họ tên bắt buộc và tối đa
255 ký tự; email phải hợp lệ và tối đa 255 ký tự. Tên đăng nhập/email được bỏ khoảng
trắng ở hai đầu và chuyển chữ thường. Mật khẩu dài 8–128 ký tự và phải khớp xác nhận.
Thành công trả HTTP 201 với `userId,username,fullName,email`; không trả mật khẩu/hash
hoặc token. FE chuyển về đăng nhập và điền sẵn username; đăng nhập mới cấp phiên.
Dữ liệu không hợp lệ trả 400, trùng tên đăng nhập/email trả 409.

Database cần có unique index tên đăng nhập/email theo model; startup không tự thêm
index. Luồng đăng ký có khóa trong tiến trình để kiểm tra trùng và tạo tài khoản
tuần tự, phù hợp cấu hình một worker được hướng dẫn ở trên.

Trong Swagger (`/docs`), gọi `/api/auth/login`, sao chép `data.accessToken`,
bấm **Authorize** và dán token (không thêm chữ `Bearer`). Swagger sẽ gửi token
khi gọi các API được bảo vệ, gồm cả GET. Sau khi đăng xuất, bấm Authorize → Logout
để xóa token khỏi Swagger.

## REST API giữ nguyên

| Method | Endpoint | Body/query |
| --- | --- | --- |
| GET | `/api/auth/health` | |
| GET | `/api/system/status` | `mqttConnected`, `esp32Online` (null nếu chưa biết) |
| POST | `/api/auth/register` | `username,fullName,email,password,confirmPassword` → 201; 400 nếu sai, 409 nếu trùng |
| POST | `/api/auth/login` | `{"username":"admin","password":"123456"}` |
| POST | `/api/auth/logout` | Yêu cầu Bearer token, thu hồi phiên hiện tại |
| GET | `/api/user/profile` | |
| GET | `/api/devices` | |
| GET | `/api/devices/{id}` | |
| GET | `/api/alert-counts` | Số mẫu vượt ngưỡng đã lưu lịch sử theo device ID; chưa có thì 0 |
| POST | `/api/devices/control` | `{"deviceId":1,"status":1}` (0=OFF, 1=ON) |
| GET | `/api/sensors` | |
| GET | `/api/sensors/latest` | Giá trị gần nhất của từng cảm biến |
| GET | `/api/sensors/chart` | `limit` mặc định 30, từ 1–30; ghép các cảm biến theo mốc giây, trả từ cũ đến mới, hoạt động cả khi ESP32 offline |
| GET | `/api/sensors/data` | `sensorId,startTime,endTime,page,size` tùy chọn |
| GET | `/api/sensors/filter` | Bắt buộc `type,startDate,endDate`; `page,size` tùy chọn |
| GET | `/api/history` | `deviceId,status,startTime,endTime,page,size` tùy chọn |
| GET | `/api/history/filter` | Bắt buộc `deviceId,status`; thời gian/phân trang tùy chọn |
| GET | `/api/thresholds` | Trả `values` và `confirmed` cho ba ngưỡng |
| POST | `/api/thresholds` | `{"temperature":35,"humidity":80,"light":3000}` |

Ba ngưỡng tương ứng LED1 nhiệt độ GPIO2, LED2 độ ẩm GPIO5, LED3 ánh sáng GPIO18.
Khoảng hợp lệ: nhiệt độ 0–50 °C (DHT11), độ ẩm 0–100 %, ánh sáng 0–4095 ADC.
POST gửi cấu hình retained qua `esp32/thresholds/{key}/control`;
`confirmed=true` chỉ sau phản hồi giá trị phù hợp qua topic `/status` từ ESP32.
Nếu mất broker, POST trả 503. ESP32 lưu ngưỡng trong NVS, nháy đèn khi giá trị
lớn hơn ngưỡng và trở lại trạng thái thủ công khi hết vượt ngưỡng.
ACK `ON/OFF` của đèn xác nhận trạng thái công tắc thủ công, không phải nhịp nháy.
Backend tự đếm trên bản tin số đo trực tiếp từ `esp32/sensor/data` (QoS 0).
Firmware mới gửi `thresholds` cùng mẫu, ví dụ:

```json
{"temperature":35,"humidity":65,"light":1500,"thresholds":{"temperature":30,"humidity":80,"light":3000}}
```

Với mỗi giá trị hợp lệ lớn hơn ngưỡng, backend ghi một history `ALERT/RECORDED`,
chi tiết `occurrence_count=1`, `trigger_value`, `trigger_threshold`, và tăng tổng
trong `alert_counts`. Cùng transaction với số đo: bất kỳ lỗi ghi nào cũng rollback,
không tăng tổng và không phát sự kiện thành công. Mẫu bằng/thấp hơn ngưỡng, số lỗi,
thiết bị chưa ánh xạ hoặc thiếu danh mục không tạo cảnh báo.

Firmware cũ không có `thresholds` trong payload chỉ được đếm sau khi backend đã
nhận `/status` ngưỡng. Ngưỡng mới đang chờ áp dụng không thay thế ngưỡng đã xác nhận.
Không dùng mặc định chưa biết để tạo lịch sử. Snapshot số đo retained và tổng đếm
cũ từ `esp32/leds/alert-counts` bị bỏ qua, không cộng bù cảnh báo offline.

Sau commit, backend phát `/topic/alert-counts` và `/topic/history`; API đọc tổng từ DB.
Dữ liệu mới có đúng một dòng history cho mỗi cảnh báo; các dòng gộp cũ vẫn giữ nguyên.
Khi nâng cấp, dừng backend rồi chạy `python migrate_alert_counts.py` để tạo/bổ sung
bảng và dựng lại tổng bằng SUM(occurrence_count) của các history ALERT/RECORDED.
Phần tổng cũ không có lịch sử sẽ không được giữ; migration không xóa bản ghi cũ và
có thể chạy lại. Khởi động lại backend sau migration.

Với database cũ, chạy `python migrate_live_code.py` sau khi cấu hình đủ ba LED
trong `MQTT_DEVICE_MAP`; script chỉ cập nhật danh mục đèn, giữ dữ liệu đo cũ.

Response vẫn có `success,message,data,code`. Thuộc tính camelCase, chuỗi thời gian
DTO `yyyy-MM-dd HH:mm:ss`, phân trang có `content,totalElements,totalPages,number,size,
first,last,empty,numberOfElements,pageable,sort` giống cấu trúc Page của Spring.
`page` bắt đầu từ 0. Dữ liệu sắp theo thời gian giảm dần, ID giảm dần để ổn định khi trùng thời gian.

`/api/sensors/data` và `/api/history` nhận cặp startTime/endTime theo ngày, giờ,
phút hoặc giây; bao gồm toàn bộ đơn vị cuối. Ví dụ hai giá trị `2026-10-17` lọc cả ngày.
`/filter` dùng khoảng đóng ở hai đầu theo giờ đã truyền, như backend cũ;
truy vấn sensor type giữ nguyên phân biệt hoa/thường theo database (ví dụ TEMPERATURE).
Timestamp lưu theo giờ Việt Nam không kèm timezone, tương thích datetime cũ.

Các lỗi input trả 400 với envelope, đăng nhập sai 401, thiết bị không có 404.
Điều khiển khi broker chưa kết nối trả 503, LED chưa ánh xạ trả 400, lệnh trước
đang chờ phản hồi trả 409. Không báo thành công giả khi publish lỗi.

`/api/devices` và `/api/devices/{id}` bổ sung `controllable`, `controlPin`, `pending`
để frontend chỉ điều khiển LED đã ánh xạ và chờ ACK. Không ghi đè metadata GPIO cũ.
`/api/sensors/data` hỗ trợ thêm `sensorType` (không phân biệt hoa/thường) và `value`
(tìm chuỗi trong giá trị số). `/api/history` hỗ trợ thêm `action=ON|OFF` và
`sort=asc|desc`. Các tham số cũ giữ nguyên.

## MQTT theo firmware ESP32 đã cung cấp

```dotenv
MQTT_HOST=127.0.0.1
MQTT_PORT=1884
MQTT_USERNAME=B23DCCN294
MQTT_PASSWORD=<mat-khau-da-cau-hinh>
MQTT_DEVICE_MAP={"1":"led1","2":"led2","3":"led3"}
```

Key trong `MQTT_DEVICE_MAP` là **ID thật trong MySQL**, value là LED trong firmware.
Kiểm tra `GET /api/devices` trước khi cấu hình; không dựa vào GPIO cũ hay thứ tự bản ghi.
Các thiết bị cũ ngoài map vẫn được liệt kê nhưng không gửi lệnh tới LED không tồn tại.
ESP32 dùng IP laptop truy cập được trong LAN; Python dùng 127.0.0.1 nếu broker cùng máy.
Mosquitto phải cho phép kết nối từ mạch trên cổng 1884 với đúng tài khoản.

| Hướng | Topic | Payload |
| --- | --- | --- |
| Nhận | `esp32/sensor/data` | `{"temperature":28.5,"humidity":65,"light":1500,"thresholds":{"temperature":35,"humidity":80,"light":3000}}` |
| Gửi | `esp32/led1/control`, `esp32/led2/control` | `ON` hoặc `OFF` |
| Nhận | `esp32/led1/status`, `esp32/led2/status` | `ON`, `OFF`, `FAIL` |
| Nhận | `esp32/status` | Chuỗi trạng thái online/offline |

POST điều khiển giữ response `data: "OK"` và message cũ để tương thích; điều này
chỉ xác nhận lệnh đã được đưa vào hàng đợi MQTT. Thiết bị chỉ đổi trạng thái khi
ESP32 gửi ON/OFF. Mỗi lệnh tạo một history PENDING, cập nhật chính bản ghi đó thành
SUCCESS/FAILED khi ACK hoặc quá `COMMAND_TIMEOUT_SECONDS` (mặc định 15 giây).
Retained snapshot đồng bộ trạng thái nhưng không xác nhận lệnh, không tạo lịch sử giả.
FAIL không được hiểu là OFF. DHT lỗi vẫn lưu dữ liệu ánh sáng hợp lệ.

Firmware không có command ID: không thể phân biệt tuyệt đối phản hồi trễ/trùng
của hai lệnh cùng trạng thái. Backend giới hạn một lệnh đang chờ trên mỗi thiết bị.
GPIO đọc lại chỉ xác nhận mức logic; light là ADC thô, không phải lux đã hiệu chuẩn.

## WebSocket mới tại `/ws`

Đây là WebSocket JSON thường, **không phải SockJS/STOMP**. REST URL giữ nguyên;
client STOMP cũ phải đổi cách kết nối. Vue dùng WebSocket thường, tự reconnect và
lấy REST snapshot để đồng bộ lại. Khi không nhận hoạt động từ ESP32 trong 20 giây,
status coi mạch offline; dữ liệu đo hợp lệ mới sẽ cập nhật trạng thái trở lại.

```js
const ws = new WebSocket('ws://localhost:8088/ws')
ws.onopen = () => ws.send(JSON.stringify({
  type: 'auth', token: sessionStorage.getItem('accessToken'),
}))
ws.onmessage = ({ data }) => {
  const event = JSON.parse(data)
  if (event.type === 'authenticated') return // Đã xác thực, bắt đầu nhận sự kiện.
  if (event.topic === '/topic/sensors') console.log(event.data)
  if (event.topic === '/topic/device-status') console.log(event.data)
}
```

Trong trình duyệt, bản tin đầu tiên trong 5 giây phải là `{type: "auth", token: "..."}`.
Backend chỉ đăng ký nhận sự kiện sau khi xác thực và trả `{type: "authenticated"}`.
Client ngoài trình duyệt có thể dùng header `Authorization: Bearer <token>` thay thế.
Không đưa token vào URL. Sai/thiếu/hết hạn token bị đóng với code `4401`.
Phiên được kiểm tra trước mỗi sự kiện và mỗi 5 giây khi không có sự kiện; đăng xuất
hoặc hết hạn sẽ ngắt kết nối, FE xóa token và quay về đăng nhập. Kiểm tra Origin vẫn áp dụng.
Có thể lọc một kênh bằng `/ws?topic=/topic/sensors` sau khi xác thực.

```json
{"topic":"/topic/sensors","recordedAt":"2026-10-21 12:00:00","data":{"temperature":28.5,"humidity":65,"light":1500}}
```

```json
{"topic":"/topic/device-status","data":{"deviceId":1,"status":1,"timestamp":"2026-10-17 16:00:00","result":"ON"}}
```

`result` có thể ON/OFF/FAIL/TIMEOUT. `/topic/esp32-status` có `data.message`.
Khi kết nối lại, lấy REST latest/devices để đồng bộ; WebSocket không lưu sự kiện cũ.
Client chậm chỉ giữ tối đa 100 sự kiện mới nhất.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test dùng database SQLite tạm riêng cho từng test, không truy cập MySQL hay broker
thật. MQTT publish được giả lập; xử lý bản tin dùng chính service của ứng dụng.
`tests/db_setup.py` chuẩn bị bảng và dữ liệu mẫu cho DB SQLite tạm trước khi mở
TestClient; phần này không được ứng dụng import hay gọi khi chạy BE.

Phạm vi: REST API, đăng ký/PBKDF2 và login SHA-256 tương thích, profile, định dạng envelope/camelCase,
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

### Kiểm tra thủ công với MySQL/Mosquitto/ESP32

1. Cấu hình `.env`, khởi động MySQL và broker rồi chạy uvicorn theo README.
2. Đăng nhập trong `/docs`, dán token vào Authorize rồi kiểm tra `/api/devices`, `/api/sensors`. Đối chiếu MQTT_DEVICE_MAP với
   ID thật trong database và LED1/LED2/LED3 của mạch.
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

### Tài liệu tham khảo

Tham khảo [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
và [Paho MQTT Python](https://eclipse.dev/paho/clients/python/docs/).
