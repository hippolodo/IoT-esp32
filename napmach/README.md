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

Mỗi đèn có bộ đếm cảnh báo riêng. Mỗi lần đọc cảm biến hợp lệ có giá trị lớn
hơn ngưỡng cộng 1, kể cả hai lần đọc liên tiếp giống nhau. Ví dụ ngưỡng 30 °C,
hai lần đọc đều 35 °C thì tổng tăng 2. Cảm biến đọc mỗi 2 giây; vòng lặp LED
chạy mỗi 10 ms và nhịp nháy không tự cộng thêm. Bằng hoặc thấp hơn ngưỡng,
DHT lỗi và bật/tắt thủ công không cộng số đếm.

Tổng và chi tiết lần đo vượt ngưỡng cuối được lưu trong NVS, namespace `iot-alerts`,
trước khi công bố qua MQTT. Sau reset/mất điện, ESP32 khôi phục tổng và lần đọc
mới vượt ngưỡng được tính tiếp. Mất Wi-Fi/MQTT vẫn đếm. Topic retained
`esp32/leds/alert-counts` gửi tổng `{"led1":5,"led2":0,"led3":12}` mỗi 2 giây
và ngay khi kết nối lại. Payload có `details` cho từng đèn: tổng, số đo và ngưỡng
của lần đo được tính cuối cùng; không thay bằng số đo bình thường sau cảnh báo.

Firmware đọc được bộ đếm NVS bản cũ và giữ nguyên tổng khi nâng cấp; phần tổng cũ
vẫn là kết quả theo cách đếm trước đây, không thể quy đổi thành số lần đo quá khứ.
Backend lưu tổng vào MySQL. Nạp firmware bình thường giữ NVS; thao tác erase flash
sẽ xóa dữ liệu trên ESP32, vì vậy không dùng erase flash khi cần giữ bộ đếm.

Topic `esp32/thresholds/{temperature|humidity|light}/control` nhận số ngưỡng;
topic tương ứng `/status` trả ngưỡng đã lưu. Cả cấu hình và xác nhận đều retained.

## VS Code báo không tìm thấy Arduino.h / DHT.h

Khi mở cả thư mục IOT, C/C++ cần cấu hình includePath tại `.vscode` của thư mục
gốc; chỉ có cấu hình trong `napmach/.vscode` chưa đủ. Máy hiện tại đã được tạo
cấu hình cho cả hai cách mở. Chạy `Developer: Reload Window` trong Command Palette
nếu editor còn giữ lỗi cũ.

Trên máy mới, mở riêng `napmach` bằng PlatformIO, build để cài dependency rồi chạy
`PlatformIO: Rebuild C/C++ Project Index` để cập nhật IntelliSense.
