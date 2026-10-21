# Tốc độ gió và thống kê cảnh báo

## Chạy chức năng

1. Nối GPIO18 → điện trở 220–330 Ω → chân dương LED cảnh báo; chân âm LED → GND.
   Đây là LED riêng, không thay hai LED điều khiển GPIO2/GPIO5.
2. Khởi động lại backend. Startup tự tạo bảng `WindSpeed` và bổ sung cảm biến
   `WIND_SPEED` vào database hiện có, không xóa lịch sử.
3. Nạp firmware mới từ thư mục gốc dự án:

   ```powershell
   & "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run --project-dir napmach --target upload
   ```

4. Mở FE, đăng nhập. Data Sensors có bộ lọc **Tốc độ gió (Wind Speed)**.
   Menu **Cảnh báo tốc độ gió** có biểu đồ tháng, danh sách ngày và chi tiết ngày.

## Luồng dữ liệu

- `napmach/napmach.ino`: ESP32 tự random số nguyên 0–500 m/s mỗi 5 giây.
  Đây là dữ liệu giả lập trên phần cứng, không phải số đo từ cảm biến gió thật.
- Cùng topic `esp32/sensor/data`, payload thêm trường `windSpeed`, ví dụ:

  ```json
  {"temperature":28.5,"humidity":65,"light":1800,"windSpeed":350}
  ```

- LED GPIO18 đảo trạng thái mỗi 1 giây nếu `windSpeed > 300`; tắt ở `<= 300`.
  Tác vụ FreeRTOS riêng giúp cảnh báo tiếp tục hoạt động trong lúc Wi-Fi/MQTT chờ kết nối.
  Không đăng ký topic hoặc API điều khiển LED cảnh báo.
- Đèn này có một bản ghi trong `devices`, tên **Đèn cảnh báo**, loại
  `device_type=WIND_WARNING`, GPIO18. Đây chính là đèn cảnh báo gió trên Dashboard.
  API thiết bị trả `type=WIND_WARNING`, `controllable=false`; nút bật/tắt tất cả
  không tác động đèn này. Trạng thái trong DB được cập nhật theo số đo gió gần nhất.
- `backend/app/database.py`: bổ sung Sensor (`type=WIND_SPEED`, `mqtt_key=windSpeed`,
  `unit=m/s`, `module=ESP32 random 0–500`); model `WindSpeed` cho từng đợt cảnh báo.
- `backend/app/mqtt.py`: kiểm tra số hữu hạn trong khoảng 0–500, lưu từng số đo vào
  `datasensors`; lưu một `WindSpeed` khi bắt đầu đợt vượt ngưỡng.
- `frontend/src/services/system.js`: nhận WebSocket và cập nhật ô tốc độ gió Dashboard.
- `frontend/src/views/DataSensors.vue`: dùng API phân trang/bộ lọc hiện có.
- `frontend/src/views/WindAlerts.vue`: vẽ biểu đồ cột bằng Chart.js/vue-chartjs,
  chọn tháng/ngày. `frontend/src/composables/useWindAlerts.js` tải ban đầu,
  tải lại khi đổi tháng/ngày, chuyển trang hoặc nhận sự kiện `/topic/wind-alerts`
  sau khi backend lưu cảnh báo mới. Không gọi định kỳ hay theo từng số đo gió.

## Quy tắc đếm

- Một đợt bắt đầu khi giá trị từ `<=300` chuyển sang `>300`; lần đầu có dữ liệu
  nếu đã `>300` cũng tính một đợt.
- `350, 400, 450` là **một** đợt; `350, 200, 400` là **hai** đợt.
- Ngưỡng đúng 300 không cảnh báo. Số lần LED nháy không phải số cảnh báo.
- Đọc số đo gần nhất từ DB để tiếp tục đếm sau khi backend khởi động lại.
- Một đợt kéo dài qua nửa đêm được tính vào ngày bắt đầu; thời gian theo Việt Nam.
- Thống kê đủ số ngày thực tế của tháng (28/29/30/31), ngày không có cảnh báo có số 0.
- Chỉ thống kê các đợt backend đã nhận qua MQTT; không lưu bù các lần cảnh báo
  xảy ra trên ESP32 khi mất mạng.

## API (đều yêu cầu Bearer token)

| API | Kết quả |
|---|---|
| `GET /api/sensors/data?sensorType=WIND_SPEED&page=0&size=10` | Các số đo gió, mới nhất trước |
| `GET /api/sensors/latest` | Giá trị gần nhất của mỗi cảm biến, gồm WIND_SPEED |
| `GET /api/alerts/wind/summary?month=2026-10` | Tổng tháng và mảng `days` gồm `{date, count}` |
| `GET /api/alerts/wind?date=2026-10-21&page=0&size=10` | Danh sách phân trang các đợt bắt đầu trong ngày |

## Kiểm tra trên mạch

Mở Serial Monitor và theo dõi `windSpeed`: ở `>300` LED nhấp nháy, ở `<=300` LED tắt.
So sánh payload với Data Sensors (lọc WIND_SPEED), rồi chọn ngày hiện tại ở màn
cảnh báo để xem các lần bắt đầu đợt. Chọn tháng/ngày chưa có dữ liệu phải hiện số 0.
Lệnh build chỉ kiểm tra biên dịch; cần nạp và quan sát LED để xác nhận phần cứng thật.
