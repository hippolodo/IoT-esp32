package com.iot.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.iot.backend.entity.DataSensor;
import com.iot.backend.entity.Device;
import com.iot.backend.entity.History;
import com.iot.backend.entity.Sensor;
import com.iot.backend.repository.DataSensorRepository;
import com.iot.backend.repository.DeviceRepository;
import com.iot.backend.repository.HistoryRepository;
import com.iot.backend.repository.SensorRepository;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * MQTT Service - Quản lý kết nối MQTT và xử lý tin nhắn từ ESP32
 * 
 * Chức năng:
 * 1. Kết nối đến MQTT Broker
 * 2. Lắng nghe dữ liệu cảm biến từ ESP32 (iot/sensors/data)
 * 3. Lưu dữ liệu vào database và gửi real-time qua WebSocket
 * 4. Lắng nghe phản hồi trạng thái thiết bị (iot/device/{id}/status)
 * 5. Điều khiển thiết bị qua MQTT (gửi lệnh ON/OFF)
 */
@Slf4j
@Service
public class MqttService {

    @Value("${mqtt.broker.url}")
    private String brokerUrl;

    @Value("${mqtt.client.id}")
    private String clientId;

    @Value("${mqtt.username:#{null}}")
    private String username;

    @Value("${mqtt.password:#{null}}")
    private String password;

    @Value("${mqtt.topic.sensor-data}")
    private String sensorDataTopic;

    @Autowired
    private DataSensorRepository dataSensorRepository;

    @Autowired
    private SensorRepository sensorRepository;

    @Autowired
    private DeviceRepository deviceRepository;

    @Autowired
    private HistoryRepository historyRepository;

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    private MqttClient mqttClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Khởi tạo MQTT Client và kết nối đến Broker
     */
    public void connect() {
        try {
            mqttClient = new MqttClient(brokerUrl, clientId + "_" + System.currentTimeMillis());
            MqttConnectOptions options = new MqttConnectOptions();
            options.setCleanSession(true);
            options.setAutomaticReconnect(true);  // Tự động reconnect khi mất kết nối

            // Cấu hình authentication nếu có
            if (username != null && !username.isEmpty()) {
                options.setUserName(username);
                options.setPassword(password.toCharArray());
            }

            // Đặt callback để xử lý các sự kiện kết nối
            mqttClient.setCallback(new MqttCallback() {
                @Override
                public void connectionLost(Throwable cause) {
                    log.error("Mất kết nối MQTT: ", cause);
                }

                @Override
                public void messageArrived(String topic, MqttMessage message) throws Exception {
                    handleMqttMessage(topic, message);
                }

                @Override
                public void deliveryComplete(IMqttDeliveryToken token) {
                    log.debug("Gửi tin nhắn thành công: " + token.getMessageId());
                }
            });

            mqttClient.connect(options);
            log.info("Kết nối MQTT thành công đến: " + brokerUrl);

            // Subscribe các topic cần lắng nghe
            subscribeTopic(sensorDataTopic, 1);  // QoS = 1
            subscribeTopic("iot/device/+/status", 1);  // Lắng nghe status từ tất cả devices

        } catch (MqttException e) {
            log.error("Lỗi kết nối MQTT: ", e);
        }
    }

    /**
     * Subscribe một topic từ MQTT Broker
     */
    private void subscribeTopic(String topic, int qos) {
        try {
            mqttClient.subscribe(topic, qos);
            log.info("Subscribe topic thành công: " + topic);
        } catch (MqttException e) {
            log.error("Lỗi subscribe topic " + topic + ": ", e);
        }
    }

    /**
     * Xử lý tin nhắn MQTT từ ESP32
     */
    private void handleMqttMessage(String topic, MqttMessage message) {
        try {
            String payload = new String(message.getPayload());
            log.info("Nhận tin nhắn MQTT - Topic: " + topic + ", Payload: " + payload);

            if (topic.equals(sensorDataTopic)) {
                // Xử lý dữ liệu cảm biến
                handleSensorData(payload);
            } else if (topic.contains("/device/") && topic.contains("/status")) {
                // Xử lý phản hồi trạng thái thiết bị
                handleDeviceStatus(topic, payload);
            }
        } catch (Exception e) {
            log.error("Lỗi xử lý tin nhắn MQTT: ", e);
        }
    }

    /**
     * Xử lý dữ liệu cảm biến từ ESP32
     * JSON format: {"temperature": 25.5, "humidity": 60.3, "light": 750}
     */
    private void handleSensorData(String payload) {
        try {
            Map<String, Object> sensorValues = objectMapper.readValue(payload, Map.class);

            // Map tên sensor từ JSON key
            Map<String, Double> valueMap = new HashMap<>();
            for (String key : sensorValues.keySet()) {
                Object value = sensorValues.get(key);
                if (value instanceof Number) {
                    valueMap.put(key, ((Number) value).doubleValue());
                }
            }

            // Lưu dữ liệu vào database
            for (String mqttKey : valueMap.keySet()) {
                Optional<Sensor> sensorByMqttKey = sensorRepository.findByMqttKey(mqttKey);
                Sensor sensor = sensorByMqttKey
                        .or(() -> sensorRepository.findByType(mqttKey.toUpperCase(Locale.ROOT)))
                        .orElse(null);

                if (sensor != null) {
                    DataSensor dataSensor = DataSensor.builder()
                            .sensor(sensor)
                            .value(valueMap.get(mqttKey).floatValue())
                            .recordedAt(LocalDateTime.now())
                            .build();

                    dataSensorRepository.save(dataSensor);
                    log.info("Lưu dữ liệu cảm biến: " + mqttKey + " = " + valueMap.get(mqttKey));
                }
            }

            // Gửi dữ liệu real-time qua WebSocket
            messagingTemplate.convertAndSend("/topic/sensors", sensorValues);
            log.info("Gửi dữ liệu sensors qua WebSocket: " + sensorValues);

        } catch (Exception e) {
            log.error("Lỗi xử lý dữ liệu cảm biến: ", e);
        }
    }

    /**
     * Xử lý phản hồi trạng thái thiết bị từ ESP32
     * Topic format: iot/device/{deviceId}/status
     * JSON format: {"deviceId": 1, "status": 1, "pin": 5}
     */
    private void handleDeviceStatus(String topic, String payload) {
        try {
            // Extract deviceId từ topic: iot/device/1/status -> 1
            String[] parts = topic.split("/");
            Integer deviceId = Integer.parseInt(parts[2]);

            Map<String, Object> statusData = objectMapper.readValue(payload, Map.class);
            Integer status = ((Number) statusData.get("status")).intValue();

            // Cập nhật trạng thái thiết bị trong database
            Device device = deviceRepository.findById(deviceId).orElse(null);
            if (device != null) {
                device.setStatus(status);
                device.setUpdatedAt(LocalDateTime.now());
                deviceRepository.save(device);

                // Lưu lịch sử hành động
                History history = new History();
                history.setDevice(device);
                history.setAction(status == 1 ? "ON" : "OFF");
                history.setStatus("SUCCESS");
                history.setTimestamp(LocalDateTime.now());
                historyRepository.save(history);

                log.info("Cập nhật trạng thái thiết bị: " + deviceId + " -> " + status);

                // Gửi kết quả qua WebSocket
                Map<String, Object> response = new HashMap<>();
                response.put("deviceId", deviceId);
                response.put("status", status);
                response.put("timestamp", LocalDateTime.now());
                messagingTemplate.convertAndSend("/topic/device-status", response);
            }

        } catch (Exception e) {
            log.error("Lỗi xử lý trạng thái thiết bị: ", e);
        }
    }

    /**
     * Gửi lệnh điều khiển thiết bị qua MQTT
     * Lệnh được gửi tới topic: iot/device/{deviceId}/control
     */
    public void sendDeviceControl(Integer deviceId, Integer pin, String action) {
        try {
            String topic = "iot/device/" + deviceId + "/control";
            Map<String, Object> command = new HashMap<>();
            command.put("deviceId", deviceId);
            command.put("pin", pin);
            command.put("action", action);  // "ON" hoặc "OFF"

            String payload = objectMapper.writeValueAsString(command);
            mqttClient.publish(topic, payload.getBytes(), 1, false);

            log.info("Gửi lệnh điều khiển: " + payload + " đến topic: " + topic);

        } catch (MqttException e) {
            log.error("Lỗi gửi lệnh điều khiển (MQTT): ", e);
        } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
            log.error("Lỗi gửi lệnh điều khiển (JSON): ", e);
        }
    }

    /**
     * Ngắt kết nối MQTT
     */
    public void disconnect() {
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                mqttClient.disconnect();
                log.info("Ngắt kết nối MQTT");
            }
        } catch (MqttException e) {
            log.error("Lỗi ngắt kết nối MQTT: ", e);
        }
    }
}
