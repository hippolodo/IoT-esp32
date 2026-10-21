# Firmware ESP32 (Arduino/C++)

Mở thư mục `napmach` bằng VS Code + PlatformIO IDE. Board được cấu hình là
`esp32doit-devkit-v1`, giống dự án demo_mqtt có sẵn trên máy.

`platformio.ini` khai báo bộ ESP32 Arduino và các thư viện:

- PubSubClient: MQTT.
- DHT sensor library: DHT11.
- Adafruit Unified Sensor: dependency của thư viện DHT.

PlatformIO tự cài các thư viện vào `.pio/libdeps` khi build.
WiFi.h và esp_wifi.h đi kèm bộ ESP32, không cần cài thư viện WiFi riêng.
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

## Tốc độ gió giả lập và LED cảnh báo

Firmware random 0–500 m/s mỗi 5 giây, gửi thêm `windSpeed` trong JSON cảm biến.
Nối GPIO18 → điện trở 220–330 Ω → chân dương LED; chân âm LED → GND.
LED nhấp nháy khi tốc độ gió >300 m/s, tắt khi <=300 m/s, chạy bằng tác vụ riêng.
LED này không nhận lệnh điều khiển, kể cả lệnh bật/tắt tất cả.
Xem [hướng dẫn và quy tắc đếm cảnh báo](../docs/WIND_SPEED.md).

## VS Code báo không tìm thấy Arduino.h / DHT.h

Khi mở cả thư mục IOT, C/C++ cần cấu hình includePath tại `.vscode` của thư mục
gốc; chỉ có cấu hình trong `napmach/.vscode` chưa đủ. Máy hiện tại đã được tạo
cấu hình cho cả hai cách mở. Chạy `Developer: Reload Window` trong Command Palette
nếu editor còn giữ lỗi cũ.

Trên máy mới, mở riêng `napmach` bằng PlatformIO, build để cài dependency rồi chạy
`PlatformIO: Rebuild C/C++ Project Index` để cập nhật IntelliSense.
