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

Mỗi đèn có bộ đếm cảnh báo riêng trong RAM, tăng 1 khi bắt đầu một đợt vượt
ngưỡng. Nháy liên tục vẫn là 1 đợt; chỉ khi giá trị về ngưỡng hoặc thấp hơn rồi
vượt lại mới tăng tiếp. Lỗi DHT tạm thời không chia đợt cảnh báo. Bật/tắt thủ công
không được tính. Bộ đếm về 0 khi ESP32 khởi động lại;
mất Wi-Fi/MQTT vẫn đếm. Topic retained `esp32/leds/alert-counts` gửi tổng số hiện tại
`{"led1":5,"led2":0,"led3":12}` mỗi 2 giây và ngay khi kết nối lại.

Topic `esp32/thresholds/{temperature|humidity|light}/control` nhận số ngưỡng;
topic tương ứng `/status` trả ngưỡng đã lưu. Cả cấu hình và xác nhận đều retained.

## VS Code báo không tìm thấy Arduino.h / DHT.h

Khi mở cả thư mục IOT, C/C++ cần cấu hình includePath tại `.vscode` của thư mục
gốc; chỉ có cấu hình trong `napmach/.vscode` chưa đủ. Máy hiện tại đã được tạo
cấu hình cho cả hai cách mở. Chạy `Developer: Reload Window` trong Command Palette
nếu editor còn giữ lỗi cũ.

Trên máy mới, mở riêng `napmach` bằng PlatformIO, build để cài dependency rồi chạy
`PlatformIO: Rebuild C/C++ Project Index` để cập nhật IntelliSense.
