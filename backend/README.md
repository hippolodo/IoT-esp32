# IoT SmartHome Backend - Project Documentation

## 📋 Tổng quan dự án

Backend cho hệ thống nhà thông minh IoT sử dụng:
- **Java 21 + Spring Boot 3.3.x**
- **MySQL** cho lưu trữ dữ liệu
- **MQTT** để giao tiếp với ESP32
- **WebSocket STOMP** cho cập nhật real-time

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React/Vue)                 │
└────────┬─────────────────────────────────┬───────────────┘
         │ REST API + WebSocket            │ HTTP
         │                                  │
┌────────▼──────────────────────────────────▼───────────────┐
│                  Spring Boot Backend (8088)                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  REST Controllers (Auth, Device, Sensor, History)  │  │
│  └──────────────────────────────────────────────────┘  │
│                      │                                 │
│  ┌──────────────────▼──────────────────┐               │
│  │  Business Logic Services             │               │
│  │  - AuthService                       │               │
│  │  - DeviceService                     │               │
│  │  - SensorService                     │               │
│  │  - MqttService                       │               │
│  └──────────────────┬──────────────────┘               │
│                      │                                 │
│  ┌──────────────────▼──────────────────┐               │
│  │  Data Access Layer (JPA Repositories)│               │
│  └──────────────────┬──────────────────┘               │
│                      │                                 │
│  ┌──────────────────▼──────────────────┐               │
│  │  MySQL Database                       │               │
│  │  - users, devices, sensors            │               │
│  │  - datasensors, histories             │               │
│  └──────────────────────────────────────┘               │
│                      │                                 │
│  ┌──────────────────▼──────────────────┐               │
│  │  MQTT Service ◄──┐                   │               │
│  │  - Subscribe sensor data              │               │
│  │  - Publish device control             │               │
│  └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
         │ MQTT                           
         │                                
┌────────▼─────────────────────────────────┐
│    MQTT Broker (broker.emqx.io:1883)     │
└────────┬─────────────────────────────────┘
         │ MQTT
         │
    ┌────▼─────────────────┐
    │   ESP32 Microcontroller│
    │  - GPIO Control        │
    │  - Sensor Reading      │
    │  - MQTT Communication  │
    └────────────────────────┘
```

## 📦 Cấu trúc thư mục

```
backend/
├── src/main/java/com/iot/backend/
│   ├── BackendApplication.java          # Entry point
│   ├── config/
│   │   ├── CorsConfig.java              # CORS configuration
│   │   ├── WebSocketConfig.java         # WebSocket STOMP config
│   │   ├── ApplicationStartup.java       # Startup initialization
│   │   └── DataInitializer.java         # Sample data
│   ├── controller/
│   │   ├── AuthController.java          # Authentication API
│   │   ├── DeviceController.java        # Device control API
│   │   ├── SensorController.java        # Sensor data API
│   │   └── HistoryController.java       # History API
│   ├── service/
│   │   ├── MqttService.java             # MQTT communication
│   │   ├── DeviceService.java           # Device business logic
│   │   ├── SensorService.java           # Sensor business logic
│   │   └── AuthService.java             # Authentication logic
│   ├── entity/
│   │   ├── User.java
│   │   ├── Device.java
│   │   ├── Sensor.java
│   │   ├── DataSensor.java
│   │   └── History.java
│   ├── repository/
│   │   ├── UserRepository.java
│   │   ├── DeviceRepository.java
│   │   ├── SensorRepository.java
│   │   ├── DataSensorRepository.java
│   │   └── HistoryRepository.java
│   └── dto/
│       ├── LoginRequest.java
│       ├── LoginResponse.java
│       ├── ApiResponse.java
│       ├── DeviceResponse.java
│       ├── SensorDataResponse.java
│       ├── HistoryResponse.java
│       └── DeviceControlRequest.java
├── src/main/resources/
│   └── application.properties            # Configuration
├── pom.xml                               # Maven dependencies
├── TESTING.md                            # Testing guide
└── README.md                             # This file
```

## 🚀 Quick Start

### Điều kiện tiên quyết
- Java 21
- MySQL 8.0+
- Maven 3.8+
- MQTT Broker (public: broker.emqx.io)

### Setup bước 1: Database
```sql
CREATE DATABASE iot_db;
```

### Setup bước 2: Application configuration
Edit `src/main/resources/application.properties`:
```properties
spring.datasource.username=root
spring.datasource.password=YOUR_PASSWORD
```

### Setup bước 3: Build & Run
```bash
# Build
mvn clean install

# Run
mvn spring-boot:run
```

Backend sẽ khởi động tại: `http://localhost:8088`

### Setup bước 4: Test
- Mở Postman: Import từ TESTING.md
- Test API: `POST /api/auth/login`
- Username: `admin`, Password: `123456`

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/auth/login` | Đăng nhập |
| GET | `/api/auth/health` | Kiểm tra trạng thái |

### Device Management
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/devices` | Lấy tất cả thiết bị |
| GET | `/api/devices/{id}` | Lấy chi tiết thiết bị |
| POST | `/api/devices/{id}/toggle?status={0\|1}` | Điều khiển thiết bị |
| POST | `/api/devices/control` | Điều khiển (request body) |

### Sensor Data
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/sensors` | Lấy danh sách cảm biến |
| GET | `/api/sensors/latest` | Lấy dữ liệu mới nhất |
| GET | `/api/sensors/data` | Lấy dữ liệu phân trang |
| GET | `/api/sensors/filter` | Lọc dữ liệu theo loại & thời gian |

### History
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/history` | Lấy lịch sử phân trang |
| GET | `/api/history/filter` | Lọc lịch sử |

## 🔌 MQTT Topics

| Topic | Chiều | Mô tả |
|-------|-------|-------|
| `iot/sensors/data` | ← | Nhận dữ liệu cảm biến từ ESP32 |
| `iot/device/{id}/control` | → | Gửi lệnh điều khiển tới ESP32 |
| `iot/device/{id}/status` | ← | Nhận phản hồi trạng thái từ ESP32 |

### Định dạng Message

**Sensor Data** (từ ESP32):
```json
{
    "temperature": 25.5,
    "humidity": 60.3,
    "light": 750
}
```

**Device Control** (tới ESP32):
```json
{
    "deviceId": 1,
    "pin": 18,
    "action": "ON"
}
```

**Device Status** (từ ESP32):
```json
{
    "deviceId": 1,
    "status": 1,
    "pin": 18
}
```

## 🌐 WebSocket Endpoints

### Connect
```
ws://localhost:8088/ws
```

### Subscribe Topics
- `/topic/sensors` - Dữ liệu cảm biến real-time
- `/topic/device-status` - Trạng thái thiết bị real-time

## 🗄️ Database Schema

### users
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### devices
```sql
CREATE TABLE devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    pin_gpio INT,
    status INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### sensors
```sql
CREATE TABLE sensors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    type VARCHAR(50),
    unit VARCHAR(20),
    pin_gpio INT
);
```

### datasensors
```sql
CREATE TABLE datasensors (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sensor_id INT,
    value FLOAT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
);
```

### histories
```sql
CREATE TABLE histories (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id INT,
    action VARCHAR(50),
    status VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
```

## 🔐 Bảo mật

### Authentication
- Mật khẩu được mã hóa bằng SHA256
- Không sử dụng JWT (có thể thêm sau)

### CORS
- Cho phép: `localhost:*`, `127.0.0.1:*`
- Có thể cấu hình trong `CorsConfig.java`

### MQTT
- Kết nối tới public broker (không có auth mặc định)
- Có thể thêm username/password nếu cần

## 🛠️ Development Tips

### Enable Debug Logging
Edit `application.properties`:
```properties
logging.level.root=INFO
logging.level.com.iot.backend=DEBUG
logging.level.org.springframework.web=DEBUG
```

### Inspect Database
```bash
mysql -u root -p iot_db
SELECT * FROM devices;
SELECT * FROM datasensors ORDER BY recorded_at DESC LIMIT 10;
SELECT * FROM histories ORDER BY timestamp DESC LIMIT 10;
```

### Test MQTT Broker Connectivity
```bash
# Test publish
mosquitto_pub -h broker.emqx.io -t test/topic -m "Hello"

# Test subscribe
mosquitto_sub -h broker.emqx.io -t test/topic
```

## 📚 Dependencies

Main libraries:
- **Spring Boot 3.3.2**
- **Spring Data JPA**
- **Spring Web**
- **Spring WebSocket**
- **Spring Integration MQTT**
- **MySQL Connector/J**
- **Eclipse Paho MQTT Client**
- **Lombok**
- **Jackson (JSON)**

## 🐛 Troubleshooting

### MQTT Connection Failed
```
Nguyên nhân: Broker không khả dụng
Giải pháp: 
1. Kiểm tra internet
2. Thử broker khác: broker.hivemq.com:1883
3. Kiểm tra firewall port 1883
```

### WebSocket Connection Failed
```
Nguyên nhân: CORS hoặc port sai
Giải pháp:
1. Kiểm tra origin là http://localhost:xxxx
2. Kiểm tra port 8088 không bị firewall chặn
3. Restart backend
```

### Database Connection Error
```
Nguyên nhân: MySQL chưa chạy hoặc credentials sai
Giải pháp:
1. Start MySQL service
2. Verify username/password trong application.properties
3. Kiểm tra database tồn tại
```

## 📖 Complete Testing Guide

Xem file **TESTING.md** để:
- Hướng dẫn setup chi tiết
- Test API bằng Postman
- Test MQTT bằng MQTTX
- Test WebSocket real-time
- Debugging tips

## 🤝 Contributing

Khi thêm feature mới:
1. Tạo branch mới
2. Follow Java/Spring Best Practices
3. Thêm unit tests
4. Update documentation

## 📝 License

MIT License - Dự án học tập

---

**Status**: ✅ Hoàn tất phát triển  
**Last Updated**: 2024-08-18  
**Version**: 1.0.0-SNAPSHOT
