# Firmware ESP32 (Arduino/C++)

Mở thư mục `napmach` bằng VS Code + PlatformIO IDE. Board được cấu hình là
`esp32doit-devkit-v1`, giống dự án demo_mqtt có sẵn trên máy.

`platformio.ini` khai báo bộ ESP32 Arduino và các thư viện:

- PubSubClient: MQTT.
- DHT sensor library: DHT11.
- Adafruit Unified Sensor: dependency của thư viện DHT.

PlatformIO tự cài các thư viện vào `.pio/libdeps` khi build.
WiFi.h đi kèm bộ ESP32, không cần cài thư viện WiFi riêng.
Xem [tài liệu lib_deps](https://docs.platformio.org/en/latest/projectconf/sections/env/options/library/lib_deps.html).

Tại PlatformIO terminal, từ thư mục gốc dự án:

```powershell
pio run --project-dir napmach
pio run --project-dir napmach --target upload
pio device monitor --project-dir napmach --baud 115200
```

Lệnh upload chỉ dùng khi đã cắm mạch. Nếu không tự chọn được cổng, thêm
`upload_port = COMx` vào environment trong platformio.ini theo cổng thực tế.

Có thể mở `napmach.ino` bằng Arduino IDE; khi đó cài ESP32 board package cùng
ba thư viện trên trong Boards Manager/Library Manager của Arduino IDE.
Kiểm tra Wi-Fi, IP broker, cổng và tài khoản MQTT trong sketch trước khi nạp.

## Ba đèn và ba ngưỡng

LED 1 GPIO2: nhiệt độ; LED 2 GPIO5: độ ẩm; LED 3 GPIO18: ánh sáng.
Mỗi LED nối qua điện trở 220–330 Ω về GND. DHT11 dùng GPIO4, LDR dùng GPIO33.
Mặc định ngưỡng tương ứng là 35 °C, 80 %, 3000 ADC; chỉnh trên dashboard.
Giá trị lớn hơn ngưỡng làm đèn tương ứng nháy mỗi 500 ms, dù công tắc đang tắt.
Khi về ngưỡng hoặc thấp hơn, đèn trở lại trạng thái công tắc. Các công tắc là
trạng thái thủ công; ACK MQTT xác nhận trạng thái này, không phải từng nhịp nháy.
Tác vụ riêng đọc cảm biến mỗi 2 giây và nháy đèn cả khi mất kết nối.
Ngưỡng được lưu qua Preferences/NVS; không mất khi reset. Khi DHT11 lỗi, hai
đèn nhiệt độ/độ ẩm trở về trạng thái thủ công cho tới khi đọc hợp lệ trở lại.

ESP32 không đếm và không lưu bộ đếm cảnh báo trong NVS. Mỗi 2 giây, tác vụ cảm biến
chụp số đo và ngưỡng tương ứng; vòng lặp chính gửi mỗi mẫu mới tối đa một lần khi
MQTT đang kết nối. Mẫu offline bị bỏ, không xếp hàng hoặc gửi tổng để cộng bù.
Payload có dạng:

```json
{"temperature":35,"humidity":65,"light":1500,"thresholds":{"temperature":30,"humidity":80,"light":3000}}
```

Backend chỉ tăng số đếm khi nhận số đo vượt ngưỡng và lưu lịch sử thành công.
Ví dụ hai mẫu trực tiếp đều 35 °C, ngưỡng 30 °C, tạo 2 history và tăng tổng 2.
Mất mạng thì đèn vẫn tự nháy nhưng không có số đếm/lịch sử mới trên backend.
Ngưỡng vẫn lưu trong NVS namespace `iot-thresholds` để mạch cảnh báo khi offline;
namespace bộ đếm cũ không còn được sử dụng, không cần erase flash để nâng cấp.

Topic `esp32/thresholds/{temperature|humidity|light}/control` nhận số ngưỡng;
topic tương ứng `/status` trả ngưỡng đã lưu. Cả cấu hình và xác nhận đều retained.

## VS Code báo không tìm thấy Arduino.h / DHT.h

Khi mở cả thư mục IOT, C/C++ cần cấu hình includePath tại `.vscode` của thư mục
gốc; chỉ có cấu hình trong `napmach/.vscode` chưa đủ. Máy hiện tại đã được tạo
cấu hình cho cả hai cách mở. Chạy `Developer: Reload Window` trong Command Palette
nếu editor còn giữ lỗi cũ.

Trên máy mới, mở riêng `napmach` bằng PlatformIO, build để cài dependency rồi chạy
`PlatformIO: Rebuild C/C++ Project Index` để cập nhật IntelliSense.
