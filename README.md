# SmartHome IoT — ESP32, MQTT, FastAPI & Vue

Dự án giám sát nhiệt độ, độ ẩm, ánh sáng và điều khiển đèn bằng ESP32.

Đề live code: 3 đèn bật/tắt độc lập và 3 ngưỡng chỉnh trên dashboard.
Đèn 1 (GPIO2) ứng với nhiệt độ, đèn 2 (GPIO5) độ ẩm, đèn 3 (GPIO18) ánh sáng.
Khi giá trị **lớn hơn** ngưỡng, đèn tương ứng nháy mỗi 500 ms, ưu tiên hơn công tắc.
Khi giá trị về ngưỡng hoặc thấp hơn, đèn trở về trạng thái bật/tắt đã chọn.
Ngưỡng mặc định: 35 °C, 80 %, 3000 ADC. ESP32 lưu ngưỡng trong NVS và đọc cảm biến
mỗi 2 giây, tiếp tục cảnh báo khi mất mạng. DHT lỗi thì ngừng cảnh báo nhiệt độ/độ ẩm.

Dashboard hiển thị số lần cảnh báo riêng của từng đèn. Backend nhận số đo trực tiếp
qua MQTT, so sánh với ngưỡng ESP32 gửi kèm và ghi một history `ALERT/RECORDED`
cho mỗi mẫu vượt ngưỡng. Lưu số đo, lịch sử và tăng tổng trong `alert_counts` là
cùng một transaction: ghi lỗi thì rollback toàn bộ, không tăng số đếm.
Hai mẫu liên tiếp đều là 35 °C với ngưỡng 30 °C sẽ tạo 2 history và cộng 2.

ESP32 vẫn tự nháy cảnh báo khi mất mạng nhưng không giữ bộ đếm trong RAM/NVS.
Mẫu không gửi được không có lịch sử và không được đếm bù khi kết nối lại.
MQTT số đo dùng QoS 0, không retained; backend bỏ qua snapshot retained và topic
tổng đếm `esp32/leds/alert-counts` của firmware cũ. Mất broker, backend hoặc database
thì không ghi nhận được cảnh báo mới. Đây là thống kê các mẫu được lưu thành công,
không phải số lần đèn nháy vật lý.

Frontend nhận tổng mới qua WebSocket `/topic/alert-counts`; sự kiện `/topic/history`
thông báo có lịch sử mới nhưng bảng hiện chỉ tải khi mở hoặc thao tác thủ công.
Tải lại trang lấy tổng qua `GET /api/alert-counts`, chưa có thì 0.
`alert_history_details` lưu `occurrence_count=1`, tổng mới và số đo/ngưỡng của mẫu đó.
Các dòng lịch sử gộp của phiên bản cũ được giữ nguyên để tra cứu.

Khi chuyển từ cách đếm cũ, dừng backend và chạy từ thư mục gốc:

```powershell
backend/.venv/Scripts/python.exe backend/migrate_alert_counts.py
```

Migration tạo/bổ sung bảng cảnh báo và tính lại tổng từ các lần đã có lịch sử,
loại phần tổng cũ không có bản ghi tương ứng; không xóa lịch sử hoặc số đo.
Sau đó khởi động lại backend và nạp firmware mới. Ngưỡng vẫn được lưu trong NVS.

Với database cũ, cấu hình `MQTT_DEVICE_MAP={"1":"led1","2":"led2","3":"led3"}`
trong `backend/.env`, rồi chạy `backend/.venv/Scripts/python.exe backend/migrate_live_code.py`
từ thư mục gốc để cập nhật danh mục đèn. Cần **nạp lại firmware** sau khi đổi đề.

Dashboard tự lấy 30 mốc thời gian gần nhất từ database qua `/api/sensors/chart`
khi mở/tải lại trang, kể cả khi ESP32 offline (backend và database cần hoạt động).
Các số đo cùng giây được ghép thành một điểm; dữ liệu realtime tiếp tục cập nhật
theo thời gian ghi nhận của backend, luôn giữ tối đa 30 điểm.

Firmware viết bằng Arduino/C++, backend dùng Python FastAPI, frontend dùng Vue 3.
ESP32 và backend trao đổi dữ liệu qua MQTT broker Mosquitto; dữ liệu được lưu trong MySQL.

## Trạng thái dự án

| Thành phần | Hiện trạng |
| --- | --- |
| Firmware ESP32 | Đã biên dịch thành công bằng PlatformIO cho DOIT ESP32 DEVKIT V1 |
| Backend FastAPI | Có REST API, lưu dữ liệu cảm biến, xử lý MQTT, lịch sử và WebSocket |
| MySQL | Đã kiểm tra đọc dữ liệu từ database hiện có qua API |
| Frontend Vue | Đã nối REST API/WebSocket: dashboard, cảm biến, lịch sử và hồ sơ |
| Kiểm thử | Kiểm thử API/MQTT/WebSocket và frontend; kiểm tra thêm xác nhận ngưỡng và đèn thứ 3 |
| Realtime từ mạch thật | Đã nhận dữ liệu MQTT qua FastAPI và WebSocket proxy của Vite |

Dashboard hiển thị giá trị đo thật, chờ ESP32 xác nhận lệnh trước khi đổi trạng thái
đèn và báo lỗi khi timeout. Trạng thái backend/MQTT/ESP32 được theo dõi riêng;
thiết bị chưa được ánh xạ trong firmware bị vô hiệu hóa công tắc điều khiển.

## Kiến trúc

```mermaid
flowchart LR
    ESP[ESP32 · Arduino/C++] <-->|MQTT| Broker[Mosquitto · 1884]
    Broker <-->|MQTT| API[FastAPI · 8088]
    API <--> DB[(MySQL)]
    Web[Vue 3 · 5173] <-->|REST / WebSocket| API
```

## Công nghệ

- **Phần cứng:** ESP32, DHT11, cảm biến ánh sáng LDR và 3 LED.
- **Firmware:** Arduino framework, PubSubClient, DHT sensor library, Adafruit Unified Sensor.
- **Backend:** FastAPI, Uvicorn, SQLAlchemy, PyMySQL, Paho MQTT.
- **Frontend:** Vue 3, Vite, Tailwind CSS 4, Chart.js, vue-chartjs.
- **Lưu trữ và giao tiếp:** MySQL, Mosquitto, REST API, WebSocket JSON.

## Cấu trúc thư mục

```text
.
├── backend/
│   ├── app/                   # API, model, cấu hình, MQTT và WebSocket
│   ├── tests/                 # Kiểm thử backend
│   ├── .env.example           # Mẫu cấu hình môi trường
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   └── views/             # Dashboard, cảm biến, lịch sử, hồ sơ
│   ├── public/
│   └── package.json
└── napmach/
│   ├── napmach.ino            # Firmware nạp ESP32
│   ├── platformio.ini         # Board và thư viện Arduino
│   └── README.md
```

## Yêu cầu

- Python **3.11 trở lên**; môi trường kiểm tra dùng Python 3.14.
- Node.js và npm; môi trường build đã kiểm tra dùng Node.js **22.20**.
- MySQL.
- Mosquitto khi kết nối ESP32.
- VS Code với PlatformIO IDE, hoặc Arduino IDE để nạp firmware.
- ESP32 và máy chạy broker có thể truy cập nhau qua mạng.

Các lệnh dưới đây dùng **Windows PowerShell** và bắt đầu từ thư mục gốc repository.

## 1. Chuẩn bị MySQL và MQTT broker

Tạo database bằng MySQL client:

```sql
CREATE DATABASE IF NOT EXISTS iot_db CHARACTER SET utf8mb4;
```

Backend dùng database đã chuẩn bị sẵn và không tự sửa schema khi khởi động.
Các bảng chính là `users`, `devices`, `sensors`, `datasensors`, `histories`,
`auth_sessions` và `alert_counts`. Bảng bộ đếm được tạo bằng migration ở trên.

Cấu hình Mosquitto lắng nghe ở cổng **1884**, cho phép ESP32 kết nối từ mạng LAN,
và tạo tài khoản MQTT dùng chung trong backend/firmware. Cho phép cổng này qua
firewall trên máy chạy broker.
Tham khảo [hướng dẫn cấu hình xác thực Mosquitto](https://mosquitto.org/documentation/authentication-methods/).

## 2. Chạy backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền cấu hình thực tế trong `backend/.env`, ví dụ:

```dotenv
DATABASE_URL=mysql+pymysql://root:YOUR_DB_PASSWORD@127.0.0.1:3306/iot_db?charset=utf8mb4
MQTT_ENABLED=true
MQTT_HOST=127.0.0.1
MQTT_PORT=1884
MQTT_USERNAME=YOUR_MQTT_USERNAME
MQTT_PASSWORD=YOUR_MQTT_PASSWORD
MQTT_SENSOR_TOPIC=esp32/sensor/data
MQTT_DEVICE_MAP={"1":"led1","2":"led2","3":"led3"}
COMMAND_TIMEOUT_SECONDS=15
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`MQTT_DEVICE_MAP` ánh xạ **ID thiết bị trong database** tới LED của firmware.
Kiểm tra `GET /api/devices` để xác định ID đúng. Nếu broker chạy ở máy khác,
thay `MQTT_HOST` bằng địa chỉ máy đó. URL-encode mật khẩu MySQL nếu có ký tự đặc biệt.

Chạy backend bằng một worker:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8088
```

- Swagger UI: <http://localhost:8088/docs>
- Health check: <http://localhost:8088/api/auth/health>
- Đặt `MQTT_ENABLED=false` khi muốn chạy API/database mà chưa có broker.

Trên database mới, tài khoản mẫu là `admin` / `123456`.
Có thể tạo tài khoản riêng bằng **Chưa có tài khoản? Đăng ký** trên giao diện.
Form yêu cầu tên đăng nhập, họ tên, email, mật khẩu 8–128 ký tự và xác nhận mật khẩu;
kiểm tra tên/email trùng. Đăng ký thành công sẽ chuyển về đăng nhập với username điền sẵn.
Đăng nhập cấp token phiên có hiệu lực 24 giờ. Frontend tự gửi token khi gọi API;
mọi API dữ liệu, trạng thái, điều khiển và hồ sơ đều yêu cầu đăng nhập; chỉ health,
register và login công khai. WebSocket xác thực token bằng bản tin đầu tiên,
không đưa token vào URL; phiên bị thu hồi/hết hạn sẽ ngắt kết nối.
Lịch sử điều khiển mới lưu `userId`
của người đăng nhập, lịch sử cũ chưa có người thực hiện hiển thị `—`.

## 3. Chạy frontend

Mở terminal khác tại thư mục gốc repository:

```powershell
cd frontend
npm ci
npm run dev
```

Mở địa chỉ Vite hiển thị trong terminal, thường là <http://localhost:5173>.
Nếu đổi cổng khi tích hợp API, cập nhật `CORS_ORIGINS` của backend cho phù hợp.

Build frontend:

```powershell
npm run build
```

Kết quả được tạo trong `frontend/dist/`. Vite chuyển tiếp `/api` và `/ws` tới
FastAPI cổng 8088; cần chạy cả hai server. WebSocket tự kết nối lại, REST đồng bộ
trạng thái kết nối qua `/api/system/status` mỗi 5 giây. Thiết bị, số đo mới nhất, ngưỡng
và tổng cảnh báo được lấy khi khởi động/kết nối lại WebSocket, sau đó nhận cập nhật qua
WebSocket; trạng thái thiết bị được tải lại sau thao tác hoặc phản hồi điều khiển.
Hai bảng lọc/phân trang trên backend; dữ liệu bảng chỉ tải khi mở
màn hình, tải lại trang hoặc thao tác lọc, làm mới, đổi trang hay đổi số dòng.

Frontend giữ đầu mối export tại `src/services/system.js`. Trong `src/services/system/`,
`state.js` quản lý trạng thái và đăng ký sự kiện, `connection.js` quản lý REST polling,
WebSocket và vòng đời request, `commands.js` gửi lệnh điều khiển đèn và lưu ngưỡng.
Khi đăng xuất, gọi `stopSystem()` rồi `resetSystemState()` để hủy request và xóa dữ liệu;
response hoặc sự kiện của phiên cũ không được cập nhật trạng thái phiên mới.

Khi deploy, cấu hình reverse proxy cho `/api` và `/ws` về FastAPI, hoặc đặt
`VITE_API_BASE_URL` thành URL backend lúc build và thêm origin frontend vào
`CORS_ORIGINS`. Không đưa thông tin MQTT vào biến môi trường frontend.

## 4. Cấu hình và nạp ESP32

Mở thư mục `napmach` bằng VS Code + PlatformIO IDE. Trong `napmach.ino`, sửa:

- `ssid`, `password`: Wi-Fi của mạch.
- `mqtt_server`: IP máy chạy Mosquitto mà ESP32 truy cập được.
- `mqtt_port`: cổng broker, mặc định trong dự án là `1884`.
- `mqtt_user`, `mqtt_pass`: tài khoản MQTT đã cấu hình.

Nếu broker chạy cùng máy với backend, Python có thể dùng `127.0.0.1`, còn ESP32
phải dùng **IP LAN của máy đó**.

### Chân kết nối theo firmware

| Thiết bị | GPIO |
| --- | --- |
| DHT11 — chân dữ liệu | 4 |
| LDR — tín hiệu analog | 33 |
| LED 1 | 2 |
| LED 2 | 5 |
| LED 3 | 18 |

Giá trị `light` là ADC 12-bit đã đảo chiều (`4095 - analogRead(LDRPIN)`): sáng tăng, che giảm; **chưa phải lux đã hiệu chuẩn**. Cần nạp lại firmware để áp dụng; các bản ghi cũ trong database giữ nguyên giá trị trước đây.
Nếu dùng lại database cũ, đối chiếu metadata GPIO/đơn vị với phần cứng trước khi chạy.

Trong PlatformIO terminal, từ thư mục gốc repository:

```powershell
pio run --project-dir napmach
pio run --project-dir napmach --target upload
pio device monitor --project-dir napmach --baud 115200
```

PlatformIO tự tải các thư viện khai báo trong `platformio.ini`. Chỉ chạy lệnh
upload khi đã cắm mạch. Hướng dẫn Arduino IDE và xử lý IntelliSense nằm trong
[napmach/README.md](napmach/README.md).

## Giao thức MQTT

| Topic | Hướng nhìn từ ESP32 | Payload |
| --- | --- | --- |
| `esp32/sensor/data` | Gửi | JSON gồm `temperature`, `humidity`, `light` |
| `esp32/led1/control` | Nhận | `ON` / `OFF` hoặc `1` / `0` |
| `esp32/led2/control` | Nhận | `ON` / `OFF` hoặc `1` / `0` |
| `esp32/led3/control` | Nhận | `ON` / `OFF` hoặc `1` / `0` |
| `esp32/led_all/control` | Nhận | Điều khiển đồng thời ba LED |
| `esp32/led1/status` | Gửi | `ON` / `OFF` / `FAIL` |
| `esp32/led2/status` | Gửi | `ON` / `OFF` / `FAIL` |
| `esp32/led3/status` | Gửi | `ON` / `OFF` (trạng thái công tắc) |
| `esp32/thresholds/{key}/control` | Nhận | Số ngưỡng; retained, key là temperature/humidity/light |
| `esp32/thresholds/{key}/status` | Gửi | Ngưỡng ESP32 đã lưu; retained |
| `esp32/status` | Gửi | Trạng thái kết nối của mạch |

Ví dụ dữ liệu cảm biến:

```json
{"temperature":28.5,"humidity":65.0,"light":1500,"thresholds":{"temperature":35,"humidity":80,"light":3000}}
```

Backend ghi lệnh điều khiển ở trạng thái `PENDING`, cập nhật thành `SUCCESS` khi
nhận ACK phù hợp, hoặc `FAILED` khi nhận FAIL/quá thời gian chờ. Mỗi thiết bị chỉ
có một lệnh đang chờ. ACK xác nhận trạng thái bật/tắt thủ công; đèn vật lý ưu tiên
nháy khi vượt ngưỡng. Ngưỡng chỉ báo đã xác nhận sau khi ESP32 trả về giá trị tương ứng.

## REST API và WebSocket

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| GET | `/api/auth/health` | Kiểm tra backend |
| POST | `/api/auth/register` | Đăng ký tài khoản mới |
| POST | `/api/auth/login` | Đăng nhập |
| POST | `/api/auth/logout` | Thu hồi phiên đăng nhập |
| GET | `/api/user/profile` | Đọc hồ sơ người đang đăng nhập |
| GET | `/api/devices` | Danh sách thiết bị |
| GET | `/api/devices/{id}` | Chi tiết thiết bị |
| POST | `/api/devices/control` | Gửi lệnh bật/tắt |
| GET | `/api/sensors` | Danh sách cảm biến |
| GET | `/api/sensors/latest` | Giá trị mới nhất của từng cảm biến |
| GET | `/api/sensors/chart` | Tối đa 30 mốc dữ liệu cho biểu đồ |
| GET | `/api/sensors/data` | Dữ liệu đo có lọc/phân trang |
| GET | `/api/history` | Lịch sử có lọc/phân trang |
| GET | `/api/thresholds` | Ngưỡng backend đang giữ và trạng thái xác nhận |
| POST | `/api/thresholds` | Gửi ba ngưỡng tới ESP32 qua MQTT |
| GET | `/api/alert-counts` | Tổng cảnh báo hiện tại theo thiết bị |
| GET | `/api/system/status` | Trạng thái MQTT và ESP32 |

Body điều khiển:

```json
{"deviceId":1,"status":1}
```

`status=1` là bật, `status=0` là tắt. Phản hồi REST giữ cấu trúc
`success`, `message`, `data`, `code`; các API phân trang bắt đầu từ `page=0`.

WebSocket tại `ws://localhost:8088/ws` dùng JSON thường, **không dùng SockJS/STOMP**.
Sự kiện có dạng `{ "topic": "...", "data": { ... } }` với các kênh:

- `/topic/sensors`
- `/topic/device-status`
- `/topic/esp32-status`
- `/topic/thresholds`
- `/topic/alert-counts`
- `/topic/history`

Chi tiết tham số, phản hồi và ví dụ WebSocket: [backend/README.md](backend/README.md).

## Các luồng xử lý và vị trí mã nguồn

Các liên kết dưới đây trỏ tới file và dòng trong repository ở thời điểm viết tài liệu.
Khi sửa code làm số dòng thay đổi, tìm theo tên hàm đi kèm. FE là frontend Vue;
BE là backend FastAPI. Trong VS Code có thể Ctrl + click vào lời gọi hàm để tới định nghĩa.

### Tra cứu nhanh

| Luồng | Điểm bắt đầu | Hàm xử lý chính |
| --- | --- | --- |
| Khởi động, khôi phục phiên | [App.vue](frontend/src/App.vue) | `startSystem()` → `refreshSystem()`, `refreshChartHistory()`, `connect()` |
| Bật/tắt một đèn | [Dashboard.vue](frontend/src/views/Dashboard.vue#L156) | `toggleDevice()` → API → `MqttService.control()` → `setManual()` |
| Bật/tắt tất cả | [commands.js](frontend/src/services/system/commands.js#L37) | `controlAllDevices(status)` |
| Đổi ngưỡng | [Dashboard.vue](frontend/src/views/Dashboard.vue#L277) | `submitThresholds()` → `saveThresholds()` → `set_thresholds()` → `callback()` |
| Card số đo realtime | [connection.js](frontend/src/services/system/connection.js#L166) | `handleSensorEvent()` → `sensorValues()` → `system.sensors` |
| Biểu đồ | [connection.js](frontend/src/services/system/connection.js#L55) | `refreshChartHistory()` / `handleSensorEvent()` → `system.points` → `chartData` |
| Cảnh báo đèn thật | [napmach.ino](napmach/napmach.ino#L116) | `sensorTask()` |
| Ghi lịch sử và tổng cảnh báo | [mqtt.py](backend/app/services/mqtt.py#L143) | `_sensor_data()` → `_record_alert()` |
| Lọc dữ liệu, lịch sử | [usePage.js](frontend/src/composables/usePage.js) | `load()` → API → `sensor_data()` / `history()` → `paginate()` |
| Phát WebSocket | [mqtt.py](backend/app/services/mqtt.py#L29), [realtime.py](backend/app/routers/realtime.py#L50) | `hub.emit()` → `_enqueue()` → `send_events()` |

### 1. Khởi động, lấy dữ liệu ban đầu và giữ kết nối

1. Sau khi đăng nhập hoặc khôi phục token qua `GET /api/user/profile`,
   [App.vue](frontend/src/App.vue) gọi `startSystem()`.
2. [connection.js:243](frontend/src/services/system/connection.js#L243) tạo phiên đồng bộ mới,
   gọi `refreshSystem()`, `refreshChartHistory()` và `connect()`.
3. `refreshSystem()` lấy `/api/system/status`, `/api/devices`, `/api/sensors/latest`,
   `/api/thresholds`, `/api/alert-counts` để có dữ liệu ban đầu.
4. `connect()` mở `/ws`; khi kết nối mở, FE gửi `{type: "auth", token: "..."}`.
   BE kiểm tra phiên rồi trả `{type: "authenticated"}`. Khi nhận bản tin này,
   FE đồng bộ lại snapshot và tải lịch sử biểu đồ nếu không đang tải.
5. Sau đó dữ liệu thay đổi chủ yếu đi qua WebSocket. Mỗi 5 giây chỉ kiểm tra
   `/api/system/status` để phát hiện MQTT/ESP32 offline; không gọi định kỳ bốn API dữ liệu trên.
   Nếu lịch sử biểu đồ chưa tải thành công, tác vụ này cũng thử tải lại biểu đồ.
6. Mất WebSocket thì thử kết nối lại sau 3 giây; xác thực lại thành công sẽ lấy lại snapshot.
   Các phản hồi điều khiển đèn cũng gọi `refreshDevices()` để đồng bộ trạng thái và pending.
7. Đăng xuất: `stopSystem()` hủy request, đóng socket, dừng timer;
   `resetSystemState()` xóa dữ liệu của phiên cũ.

`captureSystemSession()` cung cấp `signal` để hủy request và `isCurrent()` để ngăn
response của phiên cũ cập nhật phiên mới. Các biến sequence/revision còn giúp tránh
response cũ ghi đè sự kiện mới.

### 2. Bật/tắt một đèn và xác nhận lệnh

```text
Dashboard → toggleDevice(device) → POST /api/devices/control
→ router control() → service control() → MqttService.control()
→ MQTT /control → ESP32 callback() → setManual()
→ MQTT /status → BE _device_status() → DB → WebSocket → Dashboard
```

1. [Dashboard.vue:156](frontend/src/views/Dashboard.vue#L156): `@click="toggleDevice(lamp)"`.
   `lamp` là phần tử trong `lamps`, được tính từ `system.devices`; `isOn` bằng `status === 1`.
2. [commands.js:7](frontend/src/services/system/commands.js#L7): `toggleDevice(device)` kiểm tra
   cờ đang gửi và `device.pending`, đặt `system.sending[device.id] = true`, rồi đảo trạng thái:
   đang `1` thì gửi `0`, còn lại gửi `1`.
3. `api()` trong [api.js](frontend/src/services/api.js#L25) thêm Bearer token và gửi:

   ```http
   POST /api/devices/control
   Content-Type: application/json

   {"deviceId":1,"status":1}
   ```

4. [routers/devices.py](backend/app/routers/devices.py#L26) nhận request, xác thực `current_user`,
   gọi `services/devices.py::control()`. Service kiểm tra `status` là `0` hoặc `1`,
   truyền ID người đăng nhập vào `mqtt.control()`.
5. [mqtt.py:294](backend/app/services/mqtt.py#L294): `MqttService.control()` kiểm tra thiết bị,
   ánh xạ LED, broker và lệnh đang chờ. Ghi `histories` với `PENDING`, commit rồi publish
   `ON`/`OFF` vào `esp32/{led}/control`, QoS 1, không retained.
6. [napmach.ino:185](napmach/napmach.ino#L185): `callback()` nhận lệnh, gọi `setManual(i, on)`.
   `setManual()` đặt `manualOn[i]`, gửi `ON`/`OFF` về `esp32/{led}/status`.
   `sensorTask()` áp dụng thiết lập ra GPIO; khi vượt ngưỡng thì nháy cảnh báo được ưu tiên.
7. BE nhận bản tin qua `_on_message()` → `handle_message()` → `_device_status()`
   tại [mqtt.py:258](backend/app/services/mqtt.py#L258). BE cập nhật `devices.status`;
   nếu bản tin không phải snapshot retained và khớp action đang chờ thì history thành `SUCCESS`.
   Nhận `FAIL` hoặc quá timeout thì thành `FAILED`.
8. BE phát `/topic/device-status`. FE `handleDeviceEvent()` cập nhật `system.devices`,
   gọi `refreshDevices()` để đồng bộ pending. Vue tự đổi công tắc.

HTTP thành công chỉ xác nhận bước gửi lệnh, chưa chứng minh đèn vật lý sáng.
ACK của ESP32 xác nhận thiết lập thủ công, không phải tín hiệu đo lại từ đèn.
`expire_commands()` trong [main.py](backend/app/main.py) kiểm tra mỗi giây;
`expire_pending()` chuyển lệnh quá `COMMAND_TIMEOUT_SECONDS` sang `FAILED` và phát `TIMEOUT`.

Trong `finally`, `delete system.sending[device.id]` bỏ khóa gửi HTTP; nếu lệnh vẫn đang
chờ ESP32, `device.pending` tiếp tục khóa nút. `session.isCurrent()` bảo vệ phiên mới.

### 3. Bật/tắt tất cả

[commands.js:37](frontend/src/services/system/commands.js#L37):
`controlAllDevices(1)` bật tất cả, `controlAllDevices(0)` tắt tất cả.

```js
const devices = system.devices.filter((device) => device.controllable)
const targets = devices.filter((device) => device.status !== status)
```

Chỉ gửi cho thiết bị điều khiển được và chưa ở trạng thái mong muốn.
`Promise.allSettled()` gửi một HTTP request cho mỗi đèn cần đổi và gom lỗi theo tên đèn.
`system.sendingAll` khóa thao tác chung, `system.sending[id]` khóa từng đèn.
Đây không phải đảo trạng thái từng đèn: đèn đã bật được bỏ qua khi bấm Bật tất cả.
FE hiện không dùng topic `esp32/led_all/control` cho thao tác này.

### 4. Lưu ngưỡng, ESP32 áp dụng và trả xác nhận

```text
Ô nhập draft → submitThresholds() → saveThresholds()
→ POST /api/thresholds → update_thresholds() → set_thresholds()
→ MQTT esp32/thresholds/{key}/control
→ ESP32 callback() → thresholds[] + NVS → publishThreshold()
→ MQTT esp32/thresholds/{key}/status → BE → WebSocket → FE
```

1. [Dashboard.vue:277](frontend/src/views/Dashboard.vue#L277): `submitThresholds()` lấy bản sao
   `draft` gồm `temperature`, `humidity`, `light` và gọi `saveThresholds({ ...draft })`.
2. [commands.js:87](frontend/src/services/system/commands.js#L87) gửi `POST /api/thresholds`:

   ```json
   {"temperature":35,"humidity":80,"light":3000}
   ```

3. [routers/thresholds.py](backend/app/routers/thresholds.py) nhận `ThresholdRequest`,
   kiểm tra giới hạn qua schema rồi gọi `mqtt.set_thresholds(body.model_dump())`.
4. [mqtt.py:239](backend/app/services/mqtt.py#L239): `set_thresholds()` lặp `key, value`,
   publish giá trị vào `esp32/thresholds/{key}/control`, QoS 1, retained.
   Backend cập nhật giá trị yêu cầu, đặt confirmed thành `False`, thêm vào `threshold_pending`
   và phát `/topic/thresholds` để FE hiển thị đang chờ.
5. [napmach.ino:185](napmach/napmach.ino#L185): `callback()` kiểm tra số hợp lệ và giới hạn,
   gán `thresholds[i] = value`, lưu bằng `preferences.putFloat(KEYS[i], value)`.
6. `publishThreshold(i)` tại [napmach.ino:224](napmach/napmach.ino#L224) gửi ngưỡng về
   `esp32/thresholds/{key}/status`. BE `handle_message()` đối chiếu giá trị đang chờ,
   cập nhật `applied_thresholds`, confirmed thành `True` và phát lại `/topic/thresholds`.
7. FE `handleSocketMessage()` gọi `applyThresholds()` trong
   [state.js](frontend/src/services/system/state.js#L47): gán `system.thresholds = data.values`
   và `system.thresholdConfirmed = data.confirmed`.

`GET /api/thresholds` → router `thresholds()` → `mqtt.threshold_status()` chỉ đọc
ngưỡng backend đang giữ và confirmed; không yêu cầu ESP32 đo/đọc lại ngay.
Khi ESP32 khởi động, `setup()` dùng `preferences.getFloat()` đọc ngưỡng đã lưu trong NVS.
Khi reconnect, ESP32 cũng công bố lại ngưỡng. Ba ngưỡng được gửi riêng, không phải một
transaction nguyên khối trên broker; lỗi publish giữa chừng có thể chỉ áp dụng một phần.

### 5. Số đo realtime trên card Dashboard

```text
sensorTask() đọc cảm biến → loop() publish MQTT
→ BE _sensor_data() lưu DB → /topic/sensors qua WebSocket
→ handleSensorEvent() → sensorValues() → system.sensors → card Vue
```

1. [napmach.ino:116](napmach/napmach.ino#L116): `sensorTask()` đọc DHT và LDR mỗi khoảng 2 giây,
   gán `readings[]`, chụp `sampleThresholds[]` và tăng `sampleVersion`.
2. `loop()` so sánh `sampleVersion` với `lastPublishedSample`, ghép JSON và publish vào
   `esp32/sensor/data` nếu đang kết nối MQTT. Số đo dùng QoS 0, không retained.
3. [mqtt.py:143](backend/app/services/mqtt.py#L143): `_sensor_data()` giải mã JSON,
   bỏ giá trị không hợp lệ, insert `datasensors` với thời gian `now()` của backend.
   Sau khi transaction thành công, phát `/topic/sensors` kèm `recordedAt`.
4. [connection.js:226](frontend/src/services/system/connection.js#L226): `onmessage` gọi
   `handleSocketMessage()`. Topic `/topic/sensors` được chuyển tới `handleSensorEvent()`.
5. [connection.js:82](frontend/src/services/system/connection.js#L82): `sensorValues()` gán:

   ```js
   system.sensors[key] = { value: values[key], time }
   ```

   Chỉ nhận số hữu hạn và không để mẫu cũ ghi đè mẫu mới hơn.
6. [Dashboard.vue](frontend/src/views/Dashboard.vue#L30) đọc
   `system.sensors.temperature?.value`, `humidity?.value`, `light?.value`.
   State reactive thay đổi thì card tự cập nhật. Chưa có dữ liệu thì hiện `—`.

Ban đầu card lấy số đo qua `GET /api/sensors/latest`. Khi lỗi DHT, card giữ số hợp lệ
gần nhất và hiển thị thông báo lỗi từ `system.sensorError`.

### 6. Vẽ biểu đồ: từ FE tới BE rồi trở lại FE

```text
startSystem() → refreshChartHistory() → GET /api/sensors/chart?limit=30
→ router sensor_chart() → service sensor_chart() → database
→ envelope(data) → FE mergeChartPoints() → system.points
→ chartData computed → <Line :data="chartData" :options="chartOptions" />
```

| Bước | File và dòng | Xử lý |
| --- | --- | --- |
| Gọi tải lịch sử | [connection.js:55](frontend/src/services/system/connection.js#L55) | `refreshChartHistory()` quản lý loading, hủy request cũ và bắt lỗi |
| Gửi HTTP | [connection.js:64](frontend/src/services/system/connection.js#L64), [api.js:25](frontend/src/services/api.js#L25) | Gửi `limit=30`, thêm token, `fetch()` rồi lấy `body.data` |
| Nhận request | [routers/sensors.py:25](backend/app/routers/sensors.py#L25) | `sensor_chart()` xác thực, nhận Session DB, gọi service |
| Truy vấn và ghép điểm | [services/sensors.py:36](backend/app/services/sensors.py#L36) | `sensor_chart()` chọn tối đa 30 mốc giây mới nhất từ `datasensors`, join `sensors` |
| Trả kết quả | [routers/sensors.py:28](backend/app/routers/sensors.py#L28) | Đóng gói `envelope(result, ...)` |
| Ghi state | [connection.js:70](frontend/src/services/system/connection.js#L70) | `system.points = mergeChartPoints(history, system.points)` |
| Tạo dữ liệu vẽ | [Dashboard.vue:299](frontend/src/views/Dashboard.vue#L299) | `chartData` tạo labels và ba datasets |
| Vẽ | [Dashboard.vue:95](frontend/src/views/Dashboard.vue#L95) | Component `Line` của vue-chartjs nhận dữ liệu và cấu hình |

SQL chọn 30 **mốc giây**, không phải 30 dòng số đo. Các số đo cùng giây được ghép:

```json
{"time":"2026-11-04 10:30:00","temperature":30.3,"humidity":68,"light":1297}
```

BE trả các điểm theo thứ tự cũ đến mới; thiếu cảm biến thì không tạo số đo giả.
`mergeChartPoints()` dùng `Map` ghép theo thời gian, nhận số hữu hạn, sắp xếp tăng dần
và `.slice(-30)` để giữ 30 điểm mới nhất. Ghép lịch sử với `system.points` giúp giữ
mẫu realtime đã nhận trong lúc chờ HTTP.

Khi có mẫu mới qua WebSocket, `handleSensorEvent()` cập nhật trực tiếp:

```js
system.points = mergeChartPoints(system.points, [{ time, ...event.data }])
```

Đây là dòng thêm dữ liệu realtime vào biểu đồ. Khi có mốc thứ 31, mốc cũ nhất bị loại.
Không cần gọi API lịch sử cho mỗi mẫu mới. `chartData` đọc:

```js
labels: system.points.map((row) => row.time.slice(11))
// Trong mỗi dataset, key lần lượt là temperature, humidity, light:
data: system.points.map((row) => row[key] ?? null)
```

`?? null` để trống số đo thiếu. Nhiệt độ màu đỏ và độ ẩm màu xanh dùng trục `y` bên trái
(0–100); ánh sáng màu vàng dùng `y2` bên phải (0–5000 ADC). `tension: 0.4` làm mềm đường.
Trục X dùng nhãn category nên khoảng cách điểm trên màn hình đều nhau, không tỷ lệ
với khoảng thời gian thực giữa các mẫu. Khi reconnect, FE tải lại lịch sử;
nếu ESP32 offline vẫn xem được lịch sử có sẵn trong DB.

### 7. Cảnh báo: đèn thật, ghi DB, tổng đếm và biểu tượng nháy

Ba phần này có điều kiện và nơi xử lý riêng:

| Phần | Nơi xử lý | Điều kiện |
| --- | --- | --- |
| Đèn vật lý nháy | `sensorTask()` trên ESP32 | Số đo hợp lệ lớn hơn `thresholds[i]` |
| Ghi cảnh báo, tăng tổng | `_sensor_data()` → `_record_alert()` ở BE | Mẫu trực tiếp, ngưỡng hợp lệ, tìm được cảm biến và thiết bị, transaction thành công |
| Biểu tượng nháy | `lamps` computed và CSS ở FE | Kết nối hoạt động, ngưỡng confirmed, không lỗi DHT tương ứng, số đo lớn hơn ngưỡng |

**Đèn thật:** [napmach.ino:139](napmach/napmach.ino#L139) đặt `blinking[i]` khi
`readings[i] > thresholds[i]`. Nếu đang cảnh báo, `on = current % 1000 < 500` tạo chu kỳ
500 ms bật/500 ms tắt. `digitalWrite()` áp dụng ra GPIO. Hết vượt ngưỡng thì trở về
`manualOn[i]`. Lỗi số đo thì dừng nháy cho cảm biến đó. Tác vụ chạy riêng nên vẫn
cảnh báo khi Wi-Fi/MQTT mất kết nối.

**Ngưỡng gửi cùng mẫu:** `thresholds[]` là cấu hình hiện tại; `sampleThresholds[]` là bản
chụp tại thời điểm lấy mẫu. `sensorTask()` sao chép `sampleThresholds[i] = thresholds[i]`;
`loop()` gửi mảng chụp đó trong trường JSON `thresholds`. BE `_sample_threshold()` lấy
ngưỡng từ mẫu; với payload cũ không có trường này thì dùng ngưỡng đã được ESP32 xác nhận.

**Lưu DB:** [mqtt.py:202](backend/app/services/mqtt.py#L202) `_record_alert()` thực hiện:

1. Insert `alert_counts` với tổng 1 nếu chưa có; nếu đã có thì `total = total + 1`.
2. Đọc tổng mới: `SELECT total FROM alert_counts WHERE led = :led`.
3. Insert `histories` với `action='ALERT'`, `status='RECORDED'`, `user_id=NULL`.
4. Lấy `result.lastrowid` làm `history_id`, insert `alert_history_details` gồm
   `occurrence_count=1`, `total`, `trigger_value`, `trigger_threshold`.

Số đo và các thao tác cảnh báo cùng một transaction: bất kỳ bước ghi nào lỗi thì rollback.
Ví dụ 38°C với ngưỡng 35°C tạo một cảnh báo; mẫu tiếp theo vẫn 38°C thì tiếp tục tạo
một cảnh báo nữa. Tổng đếm là **số mẫu vượt ngưỡng được lưu**, không phải số đợt vượt
ngưỡng hay số nhịp LED. Cảnh báo tự động dùng `RECORDED`, không qua `PENDING/SUCCESS`.

**Đọc tổng:** `alert_counts_status()` trong [mqtt.py:226](backend/app/services/mqtt.py#L226)
chạy `SELECT led, total FROM alert_counts`, ánh xạ LED về device ID.
`GET /api/alert-counts` lấy tổng ban đầu; sau cảnh báo mới BE phát `/topic/alert-counts`.
FE gán `system.alertCounts = event.data`; Dashboard đọc `system.alertCounts[lamp.id]`.

`alert_counts.total` là tổng hiện tại. `alert_history_details.total` là tổng tại thời điểm
tạo từng dòng lịch sử; SQL lịch sử đọc `a.total AS alert_total`, không tự cộng tổng ở đó.

**Nháy trên giao diện:** [Dashboard.vue:217](frontend/src/views/Dashboard.vue#L217) tính
`lamp.warning`. `lampIconClass()` trả `sensor-warning-blink`; CSS ở dòng 357 đặt
`animation: sensor-warning-blink 1000ms steps(1, end) infinite`.
Đèn thật và biểu tượng có cùng chu kỳ danh nghĩa nhưng không đồng bộ pha nháy.
Mẫu không gửi được khi offline không được đếm bù; tổng chỉ tăng sau khi BE lưu thành công.

### 8. Lọc dữ liệu cảm biến, lịch sử và phân trang

```text
Nhập điều kiện → handleSearch() → applied → usePage.load()
→ GET /api/sensors/data hoặc GET /api/history
→ router → service tạo WHERE → paginate() → response → bảng Vue
```

- [DataSensors.vue](frontend/src/views/DataSensors.vue): `searchType`, `searchValue` giữ
  nội dung đang nhập; `handleSearch()` chép vào `applied`, đặt trang 1 rồi `load()`.
  Loại cảm biến gửi `sensorType`; tìm số gửi `value`; chọn TIME thì cùng chuỗi thời gian
  được gửi thành `startTime` và `endTime`.
- [ActionHistory.vue](frontend/src/views/ActionHistory.vue): `searchDevice`, `searchStatus`,
  `searchAction`, `searchTime` được chép vào `applied`. Query gửi `deviceId`, `status`,
  `action`, cặp thời gian và `sort`; chọn `all` thì bỏ điều kiện tương ứng.
- [usePage.js](frontend/src/composables/usePage.js): `load()` thêm
  `page=currentPage-1`, `size=itemsPerPage`, hủy request cũ, lưu `content`,
  `totalElements`, `totalPages`. Chỉ tải lúc mount hoặc thao tác người dùng;
  không có timer hay listener WebSocket tự tải lại hai bảng.
- [services/sensors.py](backend/app/services/sensors.py): `sensor_data()` tạo điều kiện
  theo loại, ID cảm biến, giá trị và thời gian, rồi gọi `paginate()`.
- [services/history.py](backend/app/services/history.py): `history()` gọi `time_range()`,
  chuyển sang `history_page()`. Hàm này join `histories`, `devices`, `alert_history_details`,
  lọc `h.device_id`, `h.status`, `h.action` và thời gian. `action` chỉ nhận `ON`, `OFF`, `ALERT`.

**Lọc thời gian sau khi copy rồi xóa bớt:** [contracts.py:116](backend/app/contracts.py#L116)
`parse_date()` nhận bốn định dạng. `time_range()` mở rộng mốc cuối theo độ chính xác:

| Chuỗi nhập | Phạm vi lấy khi startTime bằng endTime |
| --- | --- |
| `2026-11-04` | Cả ngày 04/11 |
| `2026-11-04 10` | Cả giờ 10 |
| `2026-11-04 10:30` | Cả phút 30 |
| `2026-11-04 10:30:24` | Cả giây 24 |

Ví dụ nhập `2026-11-04 10:30`, khoảng truy vấn là `[10:30:00, 10:31:00)`:

```sql
AND h.timestamp >= :start
AND h.timestamp < :end
```

Phải xóa về đúng một trong bốn định dạng; `10:3` hay dấu `:` ở cuối không hợp lệ.
FE chuẩn hóa dấu `T` và khoảng trắng; cần bấm Lọc/Tìm kiếm hoặc Enter để áp dụng.

**Đếm bản ghi phân trang:** [contracts.py:142](backend/app/contracts.py#L142), `paginate()`:

```sql
SELECT COUNT(*) FROM (<truy vấn đã lọc>) AS page_rows
```

Đây là tổng số bản ghi khớp bộ lọc để tính `totalElements` và `totalPages`, khác tổng
cảnh báo trong `alert_counts`. Sau đó truy vấn trang bằng `LIMIT :_limit OFFSET :_offset`.
Các giá trị người dùng truyền qua `params`, không ghép trực tiếp vào SQL.

### 9. WebSocket: nơi mở, nơi phát và nơi nhận

FE mở một kết nối `/ws`, nhiều loại sự kiện dùng chung kết nối này.
Các tên `/topic/...` là trường phân loại trong JSON WebSocket, không phải topic MQTT.

```text
BE hub.emit(topic, data) → EventHub._enqueue() → queue của client
→ realtime.py::send_events() → ws.send_json(event)
→ FE connection.onmessage → handleSocketMessage() → cập nhật state
```

| Sự kiện | Nơi phát trong `backend/app/services/mqtt.py` | FE xử lý |
| --- | --- | --- |
| `/topic/sensors` | `_sensor_data()` sau lưu mẫu | `handleSensorEvent()` cập nhật card và biểu đồ |
| `/topic/device-status` | `_device_status()`, `expire_pending()` | `handleDeviceEvent()` cập nhật đèn và tải pending |
| `/topic/thresholds` | `set_thresholds()`, `handle_message()` khi nhận xác nhận | `applyThresholds()` |
| `/topic/alert-counts` | `_sensor_data()` sau ghi cảnh báo | Gán `system.alertCounts` |
| `/topic/history` | `_sensor_data()` sau ghi cảnh báo | Phát tiếp sự kiện nội bộ, bảng không tự tải |
| `/topic/esp32-status` | `handle_message()` | Cập nhật `system.esp32Online` |

Các điểm tra code:

- [connection.js:220](frontend/src/services/system/connection.js#L220): `new WebSocket(websocketUrl())`.
- Dòng 224: `connection.send(...)` gửi token; dòng 226: `onmessage` nhận bản tin.
- [api.js:69](frontend/src/services/api.js#L69): tạo URL `ws`/`wss`.
- [realtime.py:13](backend/app/routers/realtime.py#L13): endpoint `/ws`, kiểm tra Origin và token.
- [mqtt.py:29](backend/app/services/mqtt.py#L29): `EventHub.emit()` đưa sự kiện sang event loop.
- [realtime.py:61](backend/app/routers/realtime.py#L61): `await ws.send_json(event)` thực sự gửi dữ liệu.
- [connection.js:188](frontend/src/services/system/connection.js#L188): `handleSocketMessage()` phân loại.

`emitSystemEvent()` và `onSystemEvent()` trong FE là sự kiện nội bộ JavaScript, không
gửi dữ liệu qua mạng. Lệnh điều khiển và lưu ngưỡng từ FE hiện gửi bằng HTTP POST;
WebSocket dùng để nhận các cập nhật từ BE.

### 10. Các hàm trong firmware ESP32

| Hàm | File và dòng | Nhiệm vụ |
| --- | --- | --- |
| `setup()` | [napmach.ino:46](napmach/napmach.ino#L46) | Chạy một lần: đọc ngưỡng NVS, cấu hình chân/cảm biến, tạo task, bắt đầu Wi-Fi và cấu hình MQTT |
| `loop()` | [napmach.ino:73](napmach/napmach.ino#L73) | Duy trì MQTT, thử reconnect, gửi số đo mới kèm ngưỡng |
| `sensorTask()` | [napmach.ino:116](napmach/napmach.ino#L116) | Đọc cảm biến và cập nhật GPIO độc lập với mạng |
| `reconnect()` | [napmach.ino:165](napmach/napmach.ino#L165) | Kết nối broker, đăng ký Last Will, subscribe lệnh, công bố trạng thái và ngưỡng |
| `callback()` | [napmach.ino:185](napmach/napmach.ino#L185) | Nhận MQTT: áp dụng ngưỡng hoặc gọi `setManual()` |
| `setManual()` | [napmach.ino:211](napmach/napmach.ino#L211) | Gán thiết lập công tắc, gửi ON/OFF xác nhận |
| `publishThreshold()` | [napmach.ino:224](napmach/napmach.ino#L224) | Gửi ngưỡng hiện tại lên `/status` |

## Kiểm thử

Tại thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test tự động kiểm tra API, bộ lọc thời gian, MQTT handler, lịch sử và WebSocket
với database tạm. Kiểm thử trên phần cứng thật thực hiện theo
[phần kiểm thử backend](backend/README.md#kiểm-thử).

Kiểm thử frontend tại thư mục `frontend`:

```powershell
npm test
npm run build
```

Test frontend dùng HTTP/WebSocket giả lập để kiểm tra hợp đồng API, chờ ACK,
timeout, reconnect và tránh ghi đè sự kiện mới bằng snapshot cũ.

## Phần đang hoàn thiện

- Hoàn thiện chức năng hồ sơ, đổi mật khẩu và xác thực/phân quyền.
- Kiểm tra trực tiếp công tắc trên trình duyệt với đèn vật lý; hồ sơ hiện chỉ đọc.
- Bổ sung command ID trong firmware nếu cần phân biệt tuyệt đối ACK trễ/trùng.

## Trước khi đưa repository lên GitHub

File `.env`, dependency và thư mục build đã được đưa vào `.gitignore`.
Riêng sketch hiện có thông tin kết nối dùng tại máy phát triển;
thay thông tin Wi-Fi/MQTT cá nhân bằng giá trị mẫu trước khi công khai repository.
