#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Preferences.h>
#include "DHT.h"
#include <stdlib.h>
#include "AlertCounter.h"

const char* ssid = "Hi";           // Tên Wi-Fi phát từ Laptop
const char* password = "27112005"; // Mật khẩu Wi-Fi
const char* mqtt_server = "172.20.10.4"; // IP của Laptop (Broker)
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
AlertCounter alertCounters[3] = {};
portMUX_TYPE stateMux = portMUX_INITIALIZER_UNLOCKED;
unsigned long lastPublish = 0, lastReconnect = 0;

// Sampling and blinking keep running while MQTT/Wi-Fi reconnects.
void sensorTask(void*) {
  unsigned long lastSample = millis() - 2000;
  for (;;) {
    unsigned long current = millis();
    if (current - lastSample >= 2000) {
      lastSample = current;
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();
      float light = 4095 - analogRead(LDRPIN);
      portENTER_CRITICAL(&stateMux);
      readings[0] = temperature;
      readings[1] = humidity;
      readings[2] = light;
      portEXIT_CRITICAL(&stateMux);
    }
    portENTER_CRITICAL(&stateMux);
    for (int i = 0; i < 3; i++) {
      // Count one episode on entering a warning, not each physical blink.
      // Missing readings stop blinking but do not split an existing episode.
      bool valid = !isnan(readings[i]);
      blinking[i] = valid && readings[i] > thresholds[i];
      alertCounters[i] = advanceAlertCounter(alertCounters[i], valid, blinking[i]);
      bool on = blinking[i] ? (current % 1000 < 500) : manualOn[i];
      digitalWrite(LED_PINS[i], on ? HIGH : LOW);
    }
    portEXIT_CRITICAL(&stateMux);
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

void publishAlertCounts() {
  uint32_t counts[3];
  portENTER_CRITICAL(&stateMux);
  for (int i = 0; i < 3; i++) counts[i] = alertCounters[i].count;
  portEXIT_CRITICAL(&stateMux);
  String payload = "{\"led1\":" + String(counts[0]) +
                   ",\"led2\":" + String(counts[1]) +
                   ",\"led3\":" + String(counts[2]) + "}";
  client.publish("esp32/leds/alert-counts", payload.c_str(), true);
}

void publishThreshold(int i) {
  String topic = "esp32/thresholds/" + String(KEYS[i]) + "/status";
  client.publish(topic.c_str(), String(thresholds[i], 3).c_str(), true);
}

void setManual(int i, bool on) {
  portENTER_CRITICAL(&stateMux);
  manualOn[i] = on;
  portEXIT_CRITICAL(&stateMux);
  // ON/OFF acknowledges the manual setting; warning overrides the physical pin.
  client.publish(STATUS_TOPICS[i], on ? "ON" : "OFF", true);
}

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
    client.publish(STATUS_TOPICS[i], manualOn[i] ? "ON" : "OFF", true);
    publishThreshold(i);
  }
  publishAlertCounts();
}

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

void loop() {
  unsigned long current = millis();
  if (!client.connected() && current - lastReconnect >= 2000) {
    lastReconnect = current;
    reconnect();
  }
  if (client.connected()) client.loop();
  if (current - lastPublish >= 2000) {
    lastPublish = current;
    float values[3];
    portENTER_CRITICAL(&stateMux);
    for (int i = 0; i < 3; i++) values[i] = readings[i];
    portEXIT_CRITICAL(&stateMux);
    String payload = "{";
    for (int i = 0; i < 3; i++) {
      if (!isnan(values[i])) payload += "\"" + String(KEYS[i]) + "\":" + String(values[i], 1) + ",";
    }
    if (isnan(values[0]) || isnan(values[1])) payload += "\"error\":\"Loi doc DHT11!\",";
    if (payload.endsWith(",")) payload.remove(payload.length() - 1);
    payload += "}";
    Serial.println(payload);
    if (client.connected()) {
      client.publish("esp32/sensor/data", payload.c_str());
      publishAlertCounts();
    }
  }
  delay(5);
}
