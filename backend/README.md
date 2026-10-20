# IoT backend — FastAPI

Python backend thay thế Spring Boot, chạy trên cổng **8088**. Dùng SQLAlchemy/MySQL,
Paho MQTT 2 và WebSocket thường. Frontend Vue đã nối REST/WebSocket qua Vite proxy
đến cổng 8088; dashboard nhận cảm biến, điều khiển đèn và đồng bộ trạng thái thật.

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

Giữ các bảng `users`, `devices`, `sensors`, `datasensors`, `histories` cùng tên cột
snake_case của Spring Boot. Không xóa hay tự sửa dữ liệu cũ; `create_all` chỉ tạo bảng
còn thiếu, không thay thế công cụ migration khi schema thực tế khác schema trong code.
Khi khởi động, backend tạo bảng `auth_sessions` và bổ sung cột `histories.user_id`
nếu còn thiếu. Lịch sử cũ giữ nguyên, `user_id` để NULL.

Chỉ seed khi từng bảng danh mục rỗng: 2 đèn GPIO 2/5, DHT11 GPIO 4,
LDR GPIO 33 với đơn vị ADC. Database cũ giữ nguyên metadata: nếu trước đây là GPIO
18/19/21 hoặc đơn vị lux, cần đối chiếu phần cứng và cập nhật thủ công.
Các bản ghi đo và lịch sử hiện có được giữ nguyên.

Tài khoản mới trên database trống: `admin` / `123456`. Có thể tạo tài khoản bằng
nút **Chưa có tài khoản? Đăng ký** trên FE hoặc `POST /api/auth/register`.
Tài khoản mới dùng PBKDF2-SHA256 (600.000 vòng, salt ngẫu nhiên); đăng nhập vẫn
đọc SHA-256 để tương thích tài khoản Java/seed cũ. Đăng nhập trả `accessToken` có hiệu lực 24 giờ;
frontend giữ token trong `sessionStorage` và gửi header `Authorization: Bearer <accessToken>`.
Điều khiển thiết bị và xem hồ sơ yêu cầu token hợp lệ; hồ sơ trả đúng người đăng nhập,
không trả `passwordHash`. Đăng xuất thu hồi token phía backend.
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

Backend thêm unique index tên đăng nhập/email vào database cũ khi dữ liệu cho phép,
không xóa/sửa tài khoản hiện có. Nếu có dữ liệu trùng từ trước, giữ nguyên dữ liệu,
ghi log và bỏ qua index tương ứng. Luồng đăng ký có khóa trong tiến trình để kiểm tra
trùng và tạo tài khoản tuần tự, phù hợp cấu hình một worker được hướng dẫn ở trên.

Trong Swagger (`/docs`), gọi `/api/auth/login`, sao chép `data.accessToken`,
bấm **Authorize** và dán token (không thêm chữ `Bearer`). Swagger sẽ gửi token
khi gọi API điều khiển, hồ sơ và đăng xuất. Sau khi đăng xuất, bấm Authorize → Logout
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
| POST | `/api/devices/control` | `{"deviceId":1,"status":1}` (0=OFF, 1=ON) |
| GET | `/api/sensors` | |
| GET | `/api/sensors/latest` | Giá trị gần nhất của từng cảm biến |
| GET | `/api/sensors/data` | `sensorId,startTime,endTime,page,size` tùy chọn |
| GET | `/api/sensors/filter` | Bắt buộc `type,startDate,endDate`; `page,size` tùy chọn |
| GET | `/api/history` | `deviceId,status,startTime,endTime,page,size` tùy chọn |
| GET | `/api/history/filter` | Bắt buộc `deviceId,status`; thời gian/phân trang tùy chọn |

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
MQTT_DEVICE_MAP={"1":"led1","2":"led2"}
```

Key trong `MQTT_DEVICE_MAP` là **ID thật trong MySQL**, value là LED trong firmware.
Kiểm tra `GET /api/devices` trước khi cấu hình; không dựa vào GPIO cũ hay thứ tự bản ghi.
Các thiết bị cũ ngoài map vẫn được liệt kê nhưng không gửi lệnh tới LED không tồn tại.
ESP32 dùng IP laptop truy cập được trong LAN; Python dùng 127.0.0.1 nếu broker cùng máy.
Mosquitto phải cho phép kết nối từ mạch trên cổng 1884 với đúng tài khoản.

| Hướng | Topic | Payload |
| --- | --- | --- |
| Nhận | `esp32/sensor/data` | `{"temperature":28.5,"humidity":65,"light":1500}` |
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
ws.onmessage = ({ data }) => {
  const event = JSON.parse(data)
  if (event.topic === '/topic/sensors') console.log(event.data)
  if (event.topic === '/topic/device-status') console.log(event.data)
}
```

Có thể lọc một kênh bằng `/ws?topic=/topic/sensors`.

```json
{"topic":"/topic/sensors","data":{"temperature":28.5,"humidity":65,"light":1500}}
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

Xem [TESTING.md](TESTING.md) cho phạm vi tự động và kiểm tra mạch thật.
Tham khảo [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
và [Paho MQTT Python](https://eclipse.dev/paho/clients/python/docs/).
