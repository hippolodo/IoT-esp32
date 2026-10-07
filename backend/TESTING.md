# IoT SmartHome Backend - Testing Guide

## Phần 1: Chuẩn bị môi trường

### 1.1 Yêu cầu tiên quyết
- **Java**: JDK 21
- **MySQL**: 8.0+
- **MQTT Broker**: Public broker (broker.emqx.io hoặc broker.hivemq.com)
- **Tools**: Postman, MQTTX, Maven

### 1.2 Tạo cơ sở dữ liệu MySQL
```sql
CREATE DATABASE iot_db;
USE iot_db;

-- Bảng users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng devices
CREATE TABLE devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    pin_gpio INT,
    status INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng sensors
CREATE TABLE sensors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50),
    unit VARCHAR(20),
    pin_gpio INT
);

-- Bảng datasensors
CREATE TABLE datasensors (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sensor_id INT NOT NULL,
    value FLOAT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
);

-- Bảng histories
CREATE TABLE histories (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    action VARCHAR(50),
    status VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
```

### 1.3 Cấu hình ứng dụng
1. Chỉnh sửa `src/main/resources/application.properties`:
   ```properties
   spring.datasource.username=root
   spring.datasource.password=<YOUR_PASSWORD>
   ```

2. MQTT Broker (tùy chọn):
   - Mặc định: `tcp://broker.emqx.io:1883`
   - Thay thế bằng broker khác nếu cần (ví dụ: `tcp://broker.hivemq.com:1883`)

### 1.4 Build và chạy ứng dụng
```bash
# Build project
mvn clean install

# Chạy ứng dụng
mvn spring-boot:run

# Hoặc chạy từ JAR
java -jar target/backend-0.0.1-SNAPSHOT.jar
```

Backend sẽ chạy tại: `http://localhost:8088`

---

## Phần 2: Kiểm tra API bằng Postman

### 2.1 Cấu hình Postman

#### Import Collection
1. Mở Postman
2. Click **Import** → **Paste Raw Text**
3. Dán nội dung dưới đây

#### Cơ bản chuẩn bị
- **Base URL**: `http://localhost:8088`
- **Headers chung**: 
  - `Content-Type: application/json`

### 2.2 Testing Auth APIs

#### 2.2.1 Health Check
```
GET {{BASE_URL}}/api/auth/health

Response (200):
{
    "success": true,
    "message": "Backend đang chạy",
    "data": "OK",
    "code": 200
}
```

#### 2.2.2 Login
```
POST {{BASE_URL}}/api/auth/login

Body (JSON):
{
    "username": "admin",
    "password": "123456"
}

Response (200):
{
    "success": true,
    "message": "Đăng nhập thành công",
    "data": {
        "userId": 1,
        "username": "admin",
        "fullName": "Nguyễn Văn A",
        "email": "admin@gmail.com",
        "success": true,
        "message": "Đăng nhập thành công"
    },
    "code": 200
}
```

### 2.3 Testing Device APIs

#### 2.3.1 Lấy danh sách thiết bị
```
GET {{BASE_URL}}/api/devices

Response (200):
{
    "success": true,
    "message": "Lấy danh sách thiết bị thành công",
    "data": [
        {
            "id": 1,
            "name": "Đèn phòng khách",
            "pinGpio": 18,
            "status": 0,
            "updatedAt": "2024-08-18 10:30:45"
        },
        {
            "id": 2,
            "name": "Đèn phòng ngủ",
            "pinGpio": 19,
            "status": 0,
            "updatedAt": "2024-08-18 10:30:45"
        },
        {
            "id": 3,
            "name": "Đèn ban công",
            "pinGpio": 21,
            "status": 0,
            "updatedAt": "2024-08-18 10:30:45"
        }
    ],
    "code": 200
}
```

#### 2.3.2 Lấy thông tin một thiết bị
```
GET {{BASE_URL}}/api/devices/1

Response (200):
{
    "success": true,
    "message": "Lấy thông tin thiết bị thành công",
    "data": {
        "id": 1,
        "name": "Đèn phòng khách",
        "pinGpio": 18,
        "status": 0,
        "updatedAt": "2024-08-18 10:30:45"
    },
    "code": 200
}
```

#### 2.3.3 Điều khiển thiết bị (Bật)
```
POST {{BASE_URL}}/api/devices/1/toggle?status=1

Response (200):
{
    "success": true,
    "message": "Bật thiết bị thành công",
    "data": "OK",
    "code": 200
}

⚠️ Ghi chú: 
- Hệ thống sẽ gửi lệnh qua MQTT tới ESP32
- Lệnh được publish tới topic: iot/device/1/control
- Message: {"deviceId": 1, "pin": 18, "action": "ON"}
```

#### 2.3.4 Điều khiển thiết bị (Tắt)
```
POST {{BASE_URL}}/api/devices/1/toggle?status=0

Response (200):
{
    "success": true,
    "message": "Tắt thiết bị thành công",
    "data": "OK",
    "code": 200
}
```

#### 2.3.5 Điều khiển thiết bị (Dùng Request Body)
```
POST {{BASE_URL}}/api/devices/control

Body (JSON):
{
    "deviceId": 2,
    "status": 1
}

Response (200):
{
    "success": true,
    "message": "Bật thiết bị thành công",
    "data": "OK",
    "code": 200
}
```

### 2.4 Testing Sensor APIs

#### 2.4.1 Lấy danh sách cảm biến
```
GET {{BASE_URL}}/api/sensors

Response (200):
{
    "success": true,
    "message": "Lấy danh sách cảm biến thành công",
    "data": [
        {
            "id": 1,
            "name": "Cảm biến Nhiệt độ",
            "type": "TEMPERATURE",
            "unit": "°C",
            "pinGpio": 4
        },
        {
            "id": 2,
            "name": "Cảm biến Độ ẩm",
            "type": "HUMIDITY",
            "unit": "%",
            "pinGpio": 4
        },
        {
            "id": 3,
            "name": "Cảm biến Ánh sáng",
            "type": "LIGHT",
            "unit": "lux",
            "pinGpio": 34
        }
    ],
    "code": 200
}
```

#### 2.4.2 Lấy 3 dữ liệu cảm biến gần nhất
```
GET {{BASE_URL}}/api/sensors/latest

Response (200):
{
    "success": true,
    "message": "Lấy dữ liệu cảm biến gần đây thành công",
    "data": [
        {
            "id": 1,
            "sensorId": 1,
            "sensorName": "Cảm biến Nhiệt độ",
            "sensorType": "TEMPERATURE",
            "unit": "°C",
            "value": 25.5,
            "recordedAt": "2024-08-18 10:30:45"
        },
        {
            "id": 2,
            "sensorId": 2,
            "sensorName": "Cảm biến Độ ẩm",
            "sensorType": "HUMIDITY",
            "unit": "%",
            "value": 60.3,
            "recordedAt": "2024-08-18 10:30:44"
        },
        {
            "id": 3,
            "sensorId": 3,
            "sensorName": "Cảm biến Ánh sáng",
            "sensorType": "LIGHT",
            "unit": "lux",
            "value": 750,
            "recordedAt": "2024-08-18 10:30:43"
        }
    ],
    "code": 200
}
```

#### 2.4.3 Lấy dữ liệu cảm biến có phân trang
```
GET {{BASE_URL}}/api/sensors/data?page=0&size=10

Response (200):
{
    "success": true,
    "message": "Lấy dữ liệu cảm biến thành công",
    "data": {
        "content": [
            {
                "id": 3,
                "sensorId": 3,
                "sensorName": "Cảm biến Ánh sáng",
                "sensorType": "LIGHT",
                "unit": "lux",
                "value": 750,
                "recordedAt": "2024-08-18 10:30:43"
            },
            {
                "id": 2,
                "sensorId": 2,
                "sensorName": "Cảm biến Độ ẩm",
                "sensorType": "HUMIDITY",
                "unit": "%",
                "value": 60.3,
                "recordedAt": "2024-08-18 10:30:44"
            },
            {
                "id": 1,
                "sensorId": 1,
                "sensorName": "Cảm biến Nhiệt độ",
                "sensorType": "TEMPERATURE",
                "unit": "°C",
                "value": 25.5,
                "recordedAt": "2024-08-18 10:30:45"
            }
        ],
        "pageable": {
            "pageNumber": 0,
            "pageSize": 10,
            "sort": {
                "empty": false,
                "sorted": true,
                "unsorted": false
            },
            "offset": 0,
            "paged": true,
            "unpaged": false
        },
        "last": true,
        "totalElements": 3,
        "totalPages": 1,
        "size": 10,
        "number": 0,
        "sort": {
            "empty": false,
            "sorted": true,
            "unsorted": false
        },
        "first": true,
        "numberOfElements": 3,
        "empty": false
    },
    "code": 200
}
```

#### 2.4.4 Lọc dữ liệu cảm biến theo loại và thời gian
```
GET {{BASE_URL}}/api/sensors/filter?type=TEMPERATURE&startDate=2024-01-01%2000:00:00&endDate=2024-12-31%2023:59:59&page=0&size=10

⚠️ Lưu ý: URL encode khoảng trắng thành %20

Response (200): Tương tự như phần 2.4.3
```

### 2.5 Testing History APIs

#### 2.5.1 Lấy lịch sử hành động có phân trang
```
GET {{BASE_URL}}/api/history?page=0&size=10

Response (200):
{
    "success": true,
    "message": "Lấy lịch sử thành công",
    "data": {
        "content": [
            {
                "id": 1,
                "deviceId": 1,
                "deviceName": "Đèn phòng khách",
                "action": "ON",
                "status": "PENDING",
                "timestamp": "2024-08-18 10:31:00"
            }
        ],
        "pageable": {...},
        "last": true,
        "totalElements": 1,
        "totalPages": 1,
        "size": 10,
        "number": 0,
        "first": true,
        "numberOfElements": 1,
        "empty": false
    },
    "code": 200
}
```

#### 2.5.2 Lọc lịch sử theo thiết bị, trạng thái và thời gian
```
GET {{BASE_URL}}/api/history/filter?deviceId=1&status=SUCCESS&startTime=2024-01-01%2000:00:00&endTime=2024-12-31%2023:59:59&page=0&size=10

Response (200): Tương tự như phần 2.5.1

⚠️ Status có thể là: SUCCESS, FAILED, PENDING
```

---

## Phần 3: Testing MQTT với MQTTX

### 3.1 Cài đặt MQTTX
- Tải từ: https://mqttx.app/
- Hỗ trợ Windows, macOS, Linux

### 3.2 Kết nối đến MQTT Broker

#### Tạo Connection mới
1. **Name**: `IoT Backend Local`
2. **Protocol**: `mqtt://`
3. **Broker Address**: `broker.emqx.io` (hoặc broker khác)
4. **Port**: `1883`
5. **Client ID**: `mqttx_client`
6. Click **Connect**

### 3.3 Testing MQTT Topics

#### 3.3.1 Subscribe topic nhận dữ liệu cảm biến
```
Topic: iot/sensors/data

Khi subscribe thành công, bạn sẽ nhận được dữ liệu cảm biến real-time:
{
    "temperature": 25.5,
    "humidity": 60.3,
    "light": 750
}
```

#### 3.3.2 Publish dữ liệu cảm biến từ ESP32
```
Topic: iot/sensors/data

Message (JSON):
{
    "temperature": 26.5,
    "humidity": 58.2,
    "light": 800
}

QoS: 1
Retain: false

Kết quả: 
- Dữ liệu được lưu vào database table: datasensors
- Dữ liệu được gửi real-time qua WebSocket tới: /topic/sensors
```

#### 3.3.3 Subscribe phản hồi trạng thái thiết bị
```
Topic: iot/device/+/status

Ký tự + là wildcard (match tất cả device ID)

Khi publish lệnh bật/tắt thiết bị, bạn sẽ nhận phản hồi:
{
    "deviceId": 1,
    "status": 1,
    "pin": 18
}
```

#### 3.3.4 Kiểm tra lệnh điều khiển thiết bị
```
Topic: iot/device/1/control

Subscribe vào topic này để xem lệnh từ Backend:
{
    "deviceId": 1,
    "pin": 18,
    "action": "ON"
}
```

---

## Phần 4: Testing WebSocket Real-time

### 4.1 Cài đặt WebSocket Client
- Dùng browser developer tools
- Hoặc dùng tool: `WebSocket King` (Chrome Extension)

### 4.2 Kết nối WebSocket
```
URL: ws://localhost:8088/ws

Để kết nối SockJS fallback, thêm:
ws://localhost:8088/ws/websocket
```

### 4.3 Subscribe Topics Real-time

#### 4.3.1 Lắng nghe dữ liệu cảm biến
```
Destination: /topic/sensors

Message nhận được (khi có dữ liệu từ MQTT):
{
    "temperature": 25.5,
    "humidity": 60.3,
    "light": 750
}
```

#### 4.3.2 Lắng nghe trạng thái thiết bị
```
Destination: /topic/device-status

Message nhận được (khi ESP32 phản hồi):
{
    "deviceId": 1,
    "status": 1,
    "timestamp": "2024-08-18T10:31:00.123456"
}
```

### 4.4 Gửi Message qua WebSocket (nếu cần)
```
Destination: /app/device/control

Message:
{
    "deviceId": 1,
    "status": 1
}
```

---

## Phần 5: Testing End-to-End Flow

### Kịch bản: Điều khiển đèn phòng khách
1. **Bước 1**: Đăng nhập
   - API: `POST /api/auth/login`
   - Username: `admin`, Password: `123456`

2. **Bước 2**: Lấy danh sách thiết bị
   - API: `GET /api/devices`
   - Tìm ID = 1 (Đèn phòng khách)

3. **Bước 3**: Bật đèn
   - API: `POST /api/devices/1/toggle?status=1`
   - Backend gửi lệnh qua MQTT tới topic: `iot/device/1/control`

4. **Bước 4**: (ESP32) Nhận lệnh và thực thi
   - ESP32 subscribe topic: `iot/device/1/control`
   - Bật đèn (GPIO 18)

5. **Bước 5**: (ESP32) Phản hồi trạng thái
   - ESP32 publish tới: `iot/device/1/status`
   - Message: `{"deviceId": 1, "status": 1, "pin": 18}`

6. **Bước 6**: Backend cập nhật
   - Lưu trạng thái vào `devices` table
   - Lưu lịch sử vào `histories` table
   - Gửi WebSocket message tới `/topic/device-status`

7. **Bước 7**: Frontend nhận cập nhật real-time
   - Cập nhật trạng thái đèn trong giao diện
   - Hiển thị lịch sử hành động

### Kiểm tra kết quả
```bash
# Kiểm tra trạng thái đèn trong database
SELECT * FROM devices WHERE id = 1;

# Kiểm tra lịch sử hành động
SELECT * FROM histories WHERE device_id = 1 ORDER BY timestamp DESC LIMIT 5;

# Kiểm tra dữ liệu cảm biến
SELECT * FROM datasensors ORDER BY recorded_at DESC LIMIT 10;
```

---

## Phần 6: Debugging Tips

### 6.1 Kiểm tra log Backend
```bash
# Backend logs sẽ hiển thị:
INFO - Kết nối MQTT thành công
INFO - Subscribe topic thành công: iot/sensors/data
INFO - Nhận tin nhắn MQTT - Topic: iot/sensors/data, Payload: {...}
INFO - Lưu dữ liệu cảm biến: temperature = 25.5
```

### 6.2 Kiểm tra kết nối MQTT
- Dùng MQTTX để test publish/subscribe
- Kiểm tra firewall cho port 1883
- Test broker connectivity: `mqtt-cli pub -h broker.emqx.io -t test -m "Hello"`

### 6.3 Kiểm tra WebSocket
- Dùng Chrome DevTools (Network → WS)
- Kiểm tra CORS headers
- Verify STOMP protocol exchange

### 6.4 Lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-----------|---------|
| `Connection refused to MQTT broker` | MQTT broker không khả dụng | Kiểm tra URL broker, firewall |
| `CORS error` | Frontend origin không được phép | Update CORS config |
| `WebSocket connection failed` | Port 8088 không mở | Check firewall, restart app |
| `Database connection error` | MySQL không chạy | Start MySQL service |
| `Password authentication failed` | Sai credentials database | Update application.properties |

---

## Phần 7: Postman Collection (JSON)

Có thể import vào Postman:

```json
{
  "info": {
    "name": "IoT Backend",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "url": "{{BASE_URL}}/api/auth/login",
            "body": {
              "raw": "{\"username\":\"admin\",\"password\":\"123456\"}"
            }
          }
        }
      ]
    },
    {
      "name": "Devices",
      "item": [
        {
          "name": "Get All Devices",
          "request": {
            "method": "GET",
            "url": "{{BASE_URL}}/api/devices"
          }
        },
        {
          "name": "Toggle Device",
          "request": {
            "method": "POST",
            "url": "{{BASE_URL}}/api/devices/1/toggle?status=1"
          }
        }
      ]
    }
  ]
}
```

---

## Phần 8: Video Demo Flow

Suggested test sequence:
1. Start Backend (mvn spring-boot:run)
2. Open MQTTX, connect to broker
3. Open Postman, test APIs
4. Subscribe MQTT topics
5. Test device control flow
6. Verify database updates
7. Test WebSocket real-time updates

---

**Chúc bạn testing thành công! 🚀**
