# SmartHome IoT — ESP32, MQTT, FastAPI & Vue

Dự án giám sát nhiệt độ, độ ẩm, ánh sáng và điều khiển đèn bằng ESP32.

Bổ sung tốc độ gió giả lập 0–500 m/s trên ESP32, LED tự cảnh báo GPIO18 khi vượt
300 m/s, bộ lọc WIND_SPEED và thống kê đợt cảnh báo theo tháng/ngày.
Xem [hướng dẫn tốc độ gió](docs/WIND_SPEED.md) để nối mạch và chạy chức năng mới.

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
| Kiểm thử | 95 kiểm thử backend và 7 kiểm thử frontend đã đạt |
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

- **Phần cứng:** ESP32, DHT11, cảm biến ánh sáng LDR và 2 LED.
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
│   ├── README.md
│   └── TESTING.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   └── views/             # Dashboard, cảm biến, lịch sử, hồ sơ
│   ├── public/
│   └── package.json
├── napmach/
│   ├── napmach.ino            # Firmware nạp ESP32
│   ├── platformio.ini         # Board và thư viện Arduino
│   └── README.md
└── documentMQTT.txt           # Ghi chú/lệnh MQTT dùng tại máy phát triển
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

Backend tạo các bảng còn thiếu khi khởi động và tạo dữ liệu mẫu nếu từng bảng
danh mục tương ứng đang rỗng. Các bảng chính là `users`, `devices`, `sensors`,
`datasensors` và `histories`.

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
MQTT_DEVICE_MAP={"1":"led1","2":"led2"}
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
trạng thái mỗi 5 giây. Hai bảng lọc/phân trang trên backend và tự cập nhật dữ liệu.

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
| `esp32/led_all/control` | Nhận | Điều khiển đồng thời hai LED |
| `esp32/led1/status` | Gửi | `ON` / `OFF` / `FAIL` |
| `esp32/led2/status` | Gửi | `ON` / `OFF` / `FAIL` |
| `esp32/status` | Gửi | Trạng thái kết nối của mạch |

Ví dụ dữ liệu cảm biến:

```json
{"temperature":28.5,"humidity":65.0,"light":1500}
```

Backend ghi lệnh điều khiển ở trạng thái `PENDING`, cập nhật thành `SUCCESS` khi
nhận ACK phù hợp, hoặc `FAILED` khi nhận FAIL/quá thời gian chờ. Mỗi thiết bị chỉ
có một lệnh đang chờ. Đọc lại GPIO xác nhận mức logic, chưa xác nhận đèn vật lý sáng.

## REST API và WebSocket

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| GET | `/api/auth/health` | Kiểm tra backend |
| POST | `/api/auth/register` | Đăng ký tài khoản mới |
| POST | `/api/auth/login` | Đăng nhập |
| GET | `/api/user/profile` | Đọc hồ sơ người đang đăng nhập |
| GET | `/api/devices` | Danh sách thiết bị |
| GET | `/api/devices/{id}` | Chi tiết thiết bị |
| POST | `/api/devices/control` | Gửi lệnh bật/tắt |
| GET | `/api/sensors` | Danh sách cảm biến |
| GET | `/api/sensors/latest` | Giá trị mới nhất của từng cảm biến |
| GET | `/api/sensors/data` | Dữ liệu đo có lọc/phân trang |
| GET | `/api/sensors/filter` | Lọc theo loại và khoảng thời gian |
| GET | `/api/history` | Lịch sử có lọc/phân trang |
| GET | `/api/history/filter` | Lọc lịch sử thiết bị |

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

Chi tiết tham số, phản hồi và ví dụ WebSocket: [backend/README.md](backend/README.md).

## Kiểm thử

Tại thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test tự động kiểm tra API, bộ lọc thời gian, MQTT handler, lịch sử và WebSocket
với database tạm. Kiểm thử trên phần cứng thật thực hiện theo
[backend/TESTING.md](backend/TESTING.md).

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
Riêng sketch và `documentMQTT.txt` hiện có thông tin kết nối dùng tại máy phát triển;
thay thông tin Wi-Fi/MQTT cá nhân bằng giá trị mẫu trước khi công khai repository.
