#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Preferences.h>
#include "DHT.h"
#include <stdlib.h>

const char* ssid = "Phan Han(Tang 3)";           // Tên Wi-Fi phát từ Laptop
const char* password = "68686868"; // Mật khẩu Wi-Fi
const char* mqtt_server = "192.168.0.102"; // IP của Laptop (Broker)
const int mqtt_port = 1884;

const char* mqtt_user = "B23DCCN294";
const char* mqtt_pass = "271105";


#define DHTPIN 4
#define LDRPIN 33
DHT dht(DHTPIN, DHT11);
WiFiClient wifi;
PubSubClient client(wifi);
Preferences preferences;
const uint8_t LED_PINS[] = {2, 5, 18};
const char* KEYS[] = {"temperature", "humidity", "light"};
const float LIMITS[] = {50, 100, 4095};
const char* CONTROL_TOPICS[] = {"esp32/led1/control", "esp32/led2/control", "esp32/led3/control"};
const char* STATUS_TOPICS[] = {"esp32/led1/status", "esp32/led2/status", "esp32/led3/status"};
float thresholds[] = {35, 80, 3000};
float readings[] = {NAN, NAN, NAN};
bool manualOn[] = {false, false, false};
bool blinking[] = {false, false, false};
// Ngưỡng được chụp cùng số đo để backend biết đúng ngưỡng của mẫu đó.
float sampleThresholds[] = {35, 80, 3000};
uint32_t sampleVersion = 0;
uint32_t lastPublishedSample = 0;
portMUX_TYPE stateMux = portMUX_INITIALIZER_UNLOCKED;
unsigned long lastReconnect = 0;

// Sampling and blinking keep running while MQTT/Wi-Fi reconnects.
// Tác vụ riêng đọc cảm biến mỗi 2 giây và nháy LED cả khi mất mạng.
// Không đếm trên mạch: chỉ backend nhận/lưu số đo mới được ghi nhận cảnh báo.
void sensorTask(void*) {
  unsigned long lastSample = millis() - 2000;
  for (;;) {
    unsigned long current = millis();
    // Chỉ có mẫu mới mỗi 2 giây
    bool sampled = current - lastSample >= 2000;
    if (sampled) {
      lastSample = current;
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();
      float light = 4095 - analogRead(LDRPIN);
      portENTER_CRITICAL(&stateMux);
      readings[0] = temperature;
      readings[1] = humidity;
      readings[2] = light;
      for (int i = 0; i < 3; i++) sampleThresholds[i] = thresholds[i];
      sampleVersion++;
      portEXIT_CRITICAL(&stateMux);
    }
    portENTER_CRITICAL(&stateMux);
    for (int i = 0; i < 3; i++) {
      bool valid = !isnan(readings[i]);
      if (valid) {
        if (readings[i] > thresholds[i]) {
          blinking[i] = true;
        } else {
          blinking[i] = false;
        }
      } else {
        blinking[i] = false;
      }
      bool on;
      if (blinking[i]) {
        on = current % 1000 < 500;
      } else {
        on = manualOn[i];
      }
      if (on) {
        digitalWrite(LED_PINS[i], HIGH);
      } else {
        digitalWrite(LED_PINS[i], LOW);
      }
    }
    portEXIT_CRITICAL(&stateMux);
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// Gửi ngưỡng hiện tại của cảm biến i lên topic /status để backend xác nhận cấu hình.
void publishThreshold(int i) {
  String topic = "esp32/thresholds/" + String(KEYS[i]) + "/status";
  client.publish(topic.c_str(), String(thresholds[i], 3).c_str(), true);
}

// Đổi thiết lập công tắc của đèn i và gửi ON/OFF; cảnh báo vẫn ưu tiên nhịp LED thực tế.
void setManual(int i, bool on) {
  portENTER_CRITICAL(&stateMux);
  manualOn[i] = on;
  portEXIT_CRITICAL(&stateMux);
  // ON/OFF acknowledges the manual setting; warning overrides the physical pin.
  if (on) {
    client.publish(STATUS_TOPICS[i], "ON", true);
  } else {
    client.publish(STATUS_TOPICS[i], "OFF", true);
  }
}

// PubSubClient gọi khi có bản tin: kiểm tra ngưỡng để áp dụng/lưu NVS, hoặc nhận lệnh ON/OFF.
void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) message += (char)payload[i];
  for (int i = 0; i < 3; i++) {
    String thresholdTopic = "esp32/thresholds/" + String(KEYS[i]) + "/control";
    if (String(topic) == thresholdTopic) {
      char* end;
      float value = strtof(message.c_str(), &end);
      if (end == message.c_str() || *end != '\0' || !isfinite(value) || value < 0 || value > LIMITS[i]) return;
      portENTER_CRITICAL(&stateMux);
      thresholds[i] = value;
      portEXIT_CRITICAL(&stateMux);
      // Ghi ngưỡng để dùng lại sau reset, sau đó gửi /status xác nhận giá trị đang dùng.
      preferences.putFloat(KEYS[i], value);
      publishThreshold(i);
      return;
    }
  }
  if (message != "ON" && message != "OFF" && message != "1" && message != "0") return;
  bool on = message == "ON" || message == "1";
  for (int i = 0; i < 3; i++) {
    if (String(topic) == CONTROL_TOPICS[i] || String(topic) == "esp32/led_all/control") setManual(i, on);
  }
}

// Khi có Wi-Fi, kết nối broker với Last Will offline, subscribe lại và công bố trạng thái hiện tại.
void reconnect() {
  if (WiFi.status() != WL_CONNECTED) return;
  String id = "ESP32-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (!client.connect(id.c_str(), mqtt_user, mqtt_pass, "esp32/status", 1, true, "STATUS: OFFLINE")) return;
  client.publish("esp32/status", "STATUS: ONLINE", true);
  client.subscribe("esp32/led_all/control");
  for (int i = 0; i < 3; i++) {
    client.subscribe(CONTROL_TOPICS[i], 1);
    String topic = "esp32/thresholds/" + String(KEYS[i]) + "/control";
    client.subscribe(topic.c_str(), 1);
    if (manualOn[i]) {
      client.publish(STATUS_TOPICS[i], "ON", true);
    } else {
      client.publish(STATUS_TOPICS[i], "OFF", true);
    }
    publishThreshold(i);
  }
}

// Chạy một lần khi khởi động: đọc NVS, cấu hình chân/thư viện, tạo tác vụ và bắt đầu Wi-Fi/MQTT.
void setup() {
  Serial.begin(115200);
  preferences.begin("iot-thresholds", false);
  for (int i = 0; i < 3; i++) {
    // On first boot the key is absent; keep the default without a failed read.
    if (preferences.isKey(KEYS[i])) {
      float saved = preferences.getFloat(KEYS[i], thresholds[i]);
      if (isfinite(saved) && saved >= 0 && saved <= LIMITS[i]) thresholds[i] = saved;
    }
    pinMode(LED_PINS[i], OUTPUT);
    digitalWrite(LED_PINS[i], LOW);
  }
  analogReadResolution(12);
  pinMode(LDRPIN, INPUT);
  pinMode(DHTPIN, INPUT_PULLUP);
  dht.begin();
  xTaskCreate(sensorTask, "sensor-led", 4096, nullptr, 1, nullptr);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid, password);
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setBufferSize(512);
  client.setSocketTimeout(1);
}

// Mỗi mẫu mới chỉ gửi một lần nếu đang có MQTT; mẫu khi offline bị bỏ, không gửi bù.
void loop() {
  unsigned long current = millis();
  if (!client.connected() && current - lastReconnect >= 2000) {
    lastReconnect = current;
    reconnect();
  }
  if (client.connected()) client.loop();

  float values[3], limits[3];
  uint32_t version;
  portENTER_CRITICAL(&stateMux);
  version = sampleVersion;
  for (int i = 0; i < 3; i++) {
    values[i] = readings[i];
    limits[i] = sampleThresholds[i];
  }
  portEXIT_CRITICAL(&stateMux);

  if (version != lastPublishedSample) {
    // Kể cả offline cũng đánh dấu đã xử lý; không có hàng đợi mẫu cũ để cộng bù.
    lastPublishedSample = version;
    String payload = "{";
    for (int i = 0; i < 3; i++) {
      if (!isnan(values[i])) payload += "\"" + String(KEYS[i]) + "\":" + String(values[i], 1) + ",";
    }
    if (isnan(values[0]) || isnan(values[1])) payload += "\"error\":\"Loi doc DHT11!\",";
    payload += "\"thresholds\":{";
    for (int i = 0; i < 3; i++) {
      if (i > 0) payload += ",";
      payload += "\"" + String(KEYS[i]) + "\":" + String(limits[i], 3);
    }
    payload += "}}";
    Serial.println(payload);
    if (client.connected()) {
      // QoS 0, không retained: backend chỉ thống kê mẫu trực tiếp nhận được.
      client.publish("esp32/sensor/data", payload.c_str());
    }
  }
  delay(5);
}
