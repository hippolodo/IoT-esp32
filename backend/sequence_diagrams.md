# Biểu đồ Sequence Diagram (Mermaid) cho 5 Use Case

Dưới đây là mã nguồn Mermaid chi tiết cho 5 Use Case của hệ thống SmartHome IoT. Bạn có thể sao chép phần mã trong các khối code và dán vào [Mermaid Live Editor](https://mermaid.live/) hoặc các công cụ hỗ trợ markdown để xem hình ảnh trực quan.

---

## 1. UC1: Hiển thị thông số nhiệt độ, độ ẩm và ánh sáng

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as Frontend Dashboard
    participant BE as Spring Boot Backend
    participant DB as MySQL Database
    participant MQTT as MQTT Broker (emqx)
    participant ESP32 as Thiết bị ESP32

    %% Luồng chạy ngầm thu thập dữ liệu
    Note over ESP32, DB: [Chu kỳ thu thập dữ liệu chạy ngầm]
    ESP32->>ESP32: Đọc dữ liệu từ DHT11 & LDR
    ESP32->>MQTT: Publish data (JSON) lên topic `hip_iot/sensors/data`
    MQTT->>BE: Chuyển tiếp gói tin sensor data
    BE->>DB: Lưu dữ liệu mới vào bảng `datasensors`

    %% Luồng người dùng mở Dashboard
    Note over User, FE: [Người dùng mở Dashboard]
    User->>FE: Truy cập Dashboard
    FE->>BE: GET /api/sensors/latest (Yêu cầu dữ liệu mới nhất)
    BE->>DB: Truy vấn dữ liệu mới nhất của từng loại cảm biến
    DB-->>BE: Trả về 3 dữ liệu mới nhất
    BE-->>FE: Trả về danh sách cảm biến kèm giá trị mới nhất
    FE->>User: Hiển thị các thông số lên card giao diện

    %% Thiết lập WebSocket
    FE->>BE: Kết nối WebSocket tại `/ws`
    BE-->>FE: Xác nhận kết nối thành công
    FE->>BE: Subscribe topic `/topic/sensors`

    %% Luồng realtime tiếp theo
    Note over ESP32, FE: [Cập nhật dữ liệu thời gian thực]
    ESP32->>MQTT: Publish dữ liệu cảm biến mới
    MQTT->>BE: Chuyển tiếp dữ liệu cảm biến mới
    BE->>DB: Lưu dữ liệu vào bảng `datasensors`
    BE->>FE: Broadcast dữ liệu mới qua WebSocket `/topic/sensors`
    FE->>FE: Cập nhật giá trị hiển thị trên các card (Nhiệt độ, Độ ẩm, Ánh sáng)
    FE->>User: Hiển thị giá trị thay đổi trực tiếp trên màn hình
```

---

## 2. UC2: Hiển thị biểu đồ biến động dữ liệu cảm biến thời gian thực

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as Frontend Dashboard (Biểu đồ)
    participant BE as Spring Boot Backend
    participant DB as MySQL Database
    participant MQTT as MQTT Broker (emqx)
    participant ESP32 as Thiết bị ESP32

    %% Dựng biểu đồ ban đầu
    Note over User, FE: [Dựng biểu đồ ban đầu khi mở trang]
    User->>FE: Click xem Biểu đồ biến động
    FE->>BE: GET /api/sensors/data?page=0&size=20 (Lấy 20 dữ liệu gần nhất)
    BE->>DB: Truy vấn 20 dữ liệu cảm biến gần nhất sắp xếp theo thời gian
    DB-->>BE: Trả về danh sách dữ liệu cảm biến
    BE-->>FE: Trả về danh sách dữ liệu cảm biến dưới dạng JSON
    FE->>FE: Sắp xếp theo thời gian tăng dần & vẽ Line Chart (Chart.js)
    FE->>User: Hiển thị biểu đồ đường ban đầu cho người dùng

    %% Kết nối WebSocket nhận realtime
    Note over FE, BE: [Đã subscribe kênh WebSocket /topic/sensors]
    
    %% Cập nhật điểm mới
    Note over ESP32, FE: [Cập nhật điểm mới trên biểu đồ]
    ESP32->>MQTT: Publish dữ liệu đo mới nhất
    MQTT->>BE: Chuyển tiếp dữ liệu đo mới
    BE->>DB: Lưu vào bảng `datasensors`
    BE->>FE: Gửi dữ liệu đo mới qua WebSocket `/topic/sensors`
    FE->>FE: 1. Push điểm mới vào cuối biểu đồ<br/>2. Shift (loại bỏ) điểm cũ nhất ở đầu biểu đồ<br/>3. Gọi hàm update() vẽ lại biểu đồ
    FE->>User: Biểu đồ dịch chuyển và vẽ thêm điểm mới trực quan
```

---

## 3. UC3: Giám sát trạng thái và điều khiển bật/tắt thiết bị

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as Frontend Dashboard
    participant BE as Spring Boot Backend
    participant DB as MySQL Database
    participant MQTT as MQTT Broker (emqx)
    participant ESP32 as Thiết bị ESP32

    %% Lấy trạng thái ban đầu
    Note over User, FE: [Lấy trạng thái thiết bị khi tải trang]
    User->>FE: Mở giao diện điều khiển thiết bị
    FE->>BE: GET /api/devices (Yêu cầu danh sách thiết bị)
    BE->>DB: Truy vấn trạng thái các thiết bị trong bảng `devices`
    DB-->>BE: Trả về danh sách thiết bị (Trạng thái 0 hoặc 1)
    BE-->>FE: Trả về danh sách thiết bị
    FE->>User: Hiển thị trạng thái các nút Switch (ON/OFF) tương ứng

    %% Thiết lập WS lắng nghe trạng thái thiết bị
    FE->>BE: Subscribe topic WebSocket `/topic/device-status`

    %% Thực hiện điều khiển
    Note over User, ESP32: [Gửi lệnh điều khiển bật/tắt]
    User->>FE: Click nút bật/tắt thiết bị (Ví dụ: Bật Đèn Phòng Khách)
    FE->>BE: POST /api/devices/control (Body: { "deviceId": 1, "status": 1 })
    
    %% Backend xử lý & gửi MQTT lệnh điều khiển
    BE->>DB: 1. Cập nhật trạng thái tạm thời trong bảng `devices` (status = 1)
    BE->>DB: 2. Lưu lịch sử hành động trong bảng `histories` (action = "ON", status = "PENDING")
    BE->>MQTT: Publish lệnh điều khiển lên topic `iot/device/1/control` (Body: { "deviceId": 1, "pin": 18, "action": "ON" })
    BE-->>FE: Trả về phản hồi HTTP 200 OK (Đã tiếp nhận lệnh)
    
    %% ESP32 thực thi lệnh
    MQTT->>ESP32: Chuyển tiếp lệnh điều khiển
    ESP32->>ESP32: Điều khiển chân GPIO 18 bật Relay/Đèn
    
    %% ESP32 phản hồi trạng thái thực tế
    ESP32->>MQTT: Publish phản hồi trạng thái lên topic `iot/device/1/status` (Body: { "deviceId": 1, "status": 1, "pin": 18 })
    MQTT->>BE: Chuyển tiếp phản hồi trạng thái từ ESP32
    
    %% Backend cập nhật kết quả cuối cùng
    BE->>DB: 1. Xác nhận trạng thái thiết bị trong bảng `devices`<br/>2. Cập nhật lịch sử trong bảng `histories` (status = "SUCCESS")
    BE->>FE: Broadcast trạng thái mới qua WebSocket `/topic/device-status` (Body: { "deviceId": 1, "status": 1 })
    FE->>FE: Cập nhật icon đèn sáng trên giao diện Dashboard
    FE->>User: Người dùng nhìn thấy đèn đổi sang trạng thái BẬT thành công
```

---

## 4. UC4: Tra cứu lịch sử dữ liệu cảm biến

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as Frontend (Trang Tra Cứu)
    participant BE as Spring Boot Backend
    participant DB as MySQL Database

    Note over User, FE: [Tìm kiếm lịch sử cảm biến]
    User->>FE: 1. Chọn loại cảm biến cần lọc (ví dụ: TEMPERATURE)<br/>2. Chọn khoảng thời gian (Từ ngày - Đến ngày)<br/>3. Chọn số trang muốn xem (Ví dụ: Trang 1, Size 10)
    User->>FE: Nhấn nút "Tìm kiếm"
    FE->>BE: GET /api/sensors/filter?type=TEMPERATURE&startDate=...&endDate=...&page=0&size=10
    BE->>DB: Thực hiện câu lệnh SQL SELECT kèm phân trang (bảng `datasensors`)
    DB-->>BE: Trả về danh sách dữ liệu và thông tin phân trang (Tổng số bản ghi, tổng số trang)
    BE-->>FE: Trả về JSON chứa Page<SensorDataResponse>
    FE->>FE: Parse dữ liệu JSON, render bảng dữ liệu (Table) và thanh phân trang (Pagination)
    FE->>User: Hiển thị bảng lịch sử đo cảm biến cùng bộ chọn trang
```

---

## 5. UC5: Tra cứu lịch sử bật/tắt thiết bị

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as Frontend (Trang Lịch Sử Thiết Bị)
    participant BE as Spring Boot Backend
    participant DB as MySQL Database

    Note over User, FE: [Tìm kiếm lịch sử điều khiển thiết bị]
    User->>FE: 1. Chọn thiết bị cụ thể (hoặc tất cả)<br/>2. Chọn trạng thái cần lọc (SUCCESS / FAILED / PENDING)<br/>3. Nhập khoảng thời gian (Từ ngày - Đến ngày)<br/>4. Chọn trang cần xem
    User->>FE: Nhấn nút "Tìm kiếm"
    FE->>BE: GET /api/history/filter?deviceId=1&status=SUCCESS&startTime=...&endTime=...&page=0&size=10
    BE->>DB: Thực hiện câu lệnh SQL SELECT kèm phân trang trên bảng `histories`
    DB-->>BE: Trả về danh sách lịch sử hành động và thông tin phân trang
    BE-->>FE: Trả về JSON chứa Page<HistoryResponse>
    FE->>FE: Render danh sách nhật ký điều khiển lên bảng dữ liệu và cập nhật thanh phân trang
    FE->>User: Hiển thị bảng lịch sử bật/tắt thiết bị (Tên thiết bị, Hành động, Kết quả, Thời gian)
```
