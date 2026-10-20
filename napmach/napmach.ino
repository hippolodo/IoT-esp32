#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_wifi.h>
#include "DHT.h"

// ==========================================
// 1. CẤU HÌNH WIFI HOTSPOT & MOSQUITTO BROKER
// ==========================================
const char* ssid = "Phan Han(Tang 3)";           // Tên Wi-Fi phát từ Laptop
const char* password = "68686868"; // Mật khẩu Wi-Fi
const char* mqtt_server = "192.168.1.82"; // IP của Laptop (Broker)
const int mqtt_port = 1884;

const char* mqtt_user = "B23DCCN294";
const char* mqtt_pass = "271105";

const char* status_topic = "esp32/status";

// ==========================================
// 2. KHAI BÁO CHÂN GPIO (Cập nhật theo thực tế)
// ==========================================
#define LDRPIN 33        // Cảm biến ánh sáng LDR cắm ở D33
#define DHTPIN 4         // Cảm biến DHT11 cắm ở D4
#define DHTTYPE DHT11

#define LED1_PIN 2
#define LED2_PIN 5

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsg = 0;
unsigned long lastReconnectAttempt = 0;
const unsigned long SENSOR_PUBLISH_INTERVAL_MS = 2000;
const unsigned long MQTT_RECONNECT_INTERVAL_MS = 2000;
const unsigned long LED_SETTLE_MS = 10;

// ==========================================
// 3. HÀM KẾT NỐI WIFI
// ==========================================
void setup_wifi() {
  delay(100);
  Serial.println("\n--- DANG KET NOI WIFI HOTSPOT ---");

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.print("Bat dau ket noi toi: ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);

    int counter = 0;
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
      counter++;

      if (counter >= 20) {
        Serial.println("\n[Loi Wi-Fi] Thu khoi dong lai card Wi-Fi...");
        WiFi.disconnect();
        delay(200);
        WiFi.begin(ssid, password);
        counter = 0;
      }
    }
  }

  esp_wifi_set_ps(WIFI_PS_NONE);
  Serial.println("\n==> WIFI DA KET NOI THANH CONG!");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());
}

// ==========================================
// 4. HÀM NHẬN LỆNH & XÁC NHẬN BẰNG digitalRead
// ==========================================
bool publishLedStatus(uint8_t pin, const char* topic, uint8_t expectedState) {
  bool success = digitalRead(pin) == expectedState;
  const char* status = success ? (expectedState == HIGH ? "ON" : "OFF") : "FAIL";
  client.publish(topic, status, true);
  return success;
}

void controlLed(uint8_t pin, const char* statusTopic, uint8_t state) {
  digitalWrite(pin, state);
  delay(LED_SETTLE_MS);
  Serial.println(publishLedStatus(pin, statusTopic, state) ? "Success" : "Failed");
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  String topicStr = String(topic);
  Serial.print("Nhan lenh Tu Mosquitto [");
  Serial.print(topicStr);
  Serial.print("]: ");
  Serial.println(message);

  uint8_t state;
  if (message == "ON" || message == "1") {
    state = HIGH;
  } else if (message == "OFF" || message == "0") {
    state = LOW;
  } else {
    return;
  }

  if (topicStr == "esp32/led1/control") {
    controlLed(LED1_PIN, "esp32/led1/status", state);
  } else if (topicStr == "esp32/led2/control") {
    controlLed(LED2_PIN, "esp32/led2/status", state);
  } else if (topicStr == "esp32/led_all/control") {
    digitalWrite(LED1_PIN, state);
    digitalWrite(LED2_PIN, state);
    delay(LED_SETTLE_MS);
    publishLedStatus(LED1_PIN, "esp32/led1/status", state);
    publishLedStatus(LED2_PIN, "esp32/led2/status", state);
    Serial.println("Success");
  }
}

// ==========================================
// 5. HÀM KẾT NỐI MQTT BROKER
// ==========================================
bool reconnect() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[LOI HE THONG] Wi-Fi bi ngat! Dang ket noi lai...");
    setup_wifi();
    return false;
  }

  Serial.print("Dang ket noi den Mosquitto (");
  Serial.print(mqtt_server);
  Serial.print(")... ");

  String clientId = "ESP32Client-";
  clientId += String(random(0xffff), HEX);

  bool isConnected = false;
  const char* willTopic = status_topic;
  const char* willMessage = "STATUS: OFFLINE (Mat ket noi dot ngot)";
  int willQoS = 1;
  bool willRetain = true;

  if (strlen(mqtt_user) > 0) {
    isConnected = client.connect(clientId.c_str(), mqtt_user, mqtt_pass, willTopic, willQoS, willRetain, willMessage);
  } else {
    isConnected = client.connect(clientId.c_str(), willTopic, willQoS, willRetain, willMessage);
  }

  if (isConnected) {
    Serial.println("Thanh cong!");
    client.subscribe("esp32/led1/control");
    client.subscribe("esp32/led2/control");
    client.subscribe("esp32/led_all/control");

    String connectMsg = "STATUS: ONLINE | IP: " + WiFi.localIP().toString();
    client.publish(status_topic, connectMsg.c_str(), true);

    // Báo cáo trạng thái thực tế ngay khi vừa khởi động
    client.publish("esp32/led1/status", digitalRead(LED1_PIN) ? "ON" : "OFF", true);
    client.publish("esp32/led2/status", digitalRead(LED2_PIN) ? "ON" : "OFF", true);

  } else {
    Serial.print("That bai! Ma loi rc=");
    Serial.println(client.state());
  }
  return client.connected();
}

// ==========================================
// 6. SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);

  pinMode(LDRPIN, INPUT);
  pinMode(DHTPIN, INPUT_PULLUP);

  dht.begin();
  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(15);
  client.setBufferSize(512);
}

// ==========================================
// 7. LOOP
// ==========================================
void loop() {
  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > MQTT_RECONNECT_INTERVAL_MS) {
      lastReconnectAttempt = now;
      if (reconnect()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    client.loop();
  }

  unsigned long now = millis();
  if (now - lastMsg > SENSOR_PUBLISH_INTERVAL_MS) {
    lastMsg = now;

    int anh_sang = analogRead(LDRPIN);
    float do_am = dht.readHumidity();
    float nhiet_do = dht.readTemperature();

    String payload = "";
    if (isnan(do_am) || isnan(nhiet_do)) {
      payload = "{\"error\": \"Loi doc DHT11!\", \"light\": " + String(anh_sang) + "}";
    } else {
      payload = "{\"light\":" + String(anh_sang) +
                ", \"temperature\":" + String(nhiet_do, 1) +
                ", \"humidity\":" + String(do_am, 1) + "}";
    }

    Serial.println(payload);

    if (client.connected()) {
      client.publish("esp32/sensor/data", payload.c_str());
    }
  }
}
