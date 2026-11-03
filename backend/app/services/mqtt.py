import json
import logging
import math
import threading
import uuid
from datetime import timedelta
from time import monotonic

import paho.mqtt.client as mqtt

from ..contracts import ControlError, date_string, execute_sql, now

log = logging.getLogger(__name__)
ESP32_OFFLINE_TIMEOUT_SECONDS = 20
MQTT_KEEPALIVE_SECONDS = 15
SENSOR_KEYS = ("temperature", "humidity", "light")
SENSOR_LEDS = {"temperature": "led1", "humidity": "led2", "light": "led3"}
THRESHOLD_LIMITS = {"temperature": 50, "humidity": 100, "light": 4095}


class EventHub:
    """Deliver MQTT thread events to bounded queues on the ASGI event loop."""
    # Khởi tạo nơi giữ event loop và các hàng đợi WebSocket đang đăng ký nhận dữ liệu.
    def __init__(self):
        self.loop = None
        self.subscribers = set()

    # Nhận sự kiện từ luồng MQTT, chuyển an toàn sang event loop để gửi cho WebSocket.
    def emit(self, topic, data, recorded_at=None):
        if self.loop and not self.loop.is_closed():
            event = {"topic": topic, "data": data}
            if recorded_at is not None:
                event["recordedAt"] = recorded_at
            self.loop.call_soon_threadsafe(self._enqueue, event)

    # Đưa sự kiện vào từng hàng đợi; hàng đợi đầy thì bỏ sự kiện cũ nhất.
    def _enqueue(self, event):
        for queue in tuple(self.subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)


class MqttService:
    # Tạo MQTT client, trạng thái kết nối/ngưỡng và các callback nhận bản tin.
    def __init__(self, settings, session_factory, hub):
        self.settings, self.sessions, self.hub = settings, session_factory, hub
        self.lock = threading.RLock()
        self.esp_online = None
        self.last_seen = None
        self.thresholds = dict(temperature=35.0, humidity=80.0, light=3000.0)
        self.threshold_confirmed = {key: False for key in SENSOR_KEYS}
        self.threshold_pending = set()
        # Ngưỡng đã được thiết bị xác nhận, tách khỏi giá trị mới đang chờ áp dụng.
        self.applied_thresholds = {key: None for key in SENSOR_KEYS}
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"iot-python-{uuid.uuid4().hex}")
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    # Bắt đầu kết nối và luồng mạng MQTT nếu MQTT_ENABLED được bật.
    def start(self):
        if self.settings.mqtt_enabled:
            self.client.connect_async(
                self.settings.mqtt_host, self.settings.mqtt_port,
                keepalive=MQTT_KEEPALIVE_SECONDS,
            )
            self.client.loop_start()

    # Ngắt client MQTT và dừng luồng mạng khi backend tắt.
    def stop(self):
        if self.settings.mqtt_enabled:
            self.client.disconnect()
            self.client.loop_stop()

    # Subscribe số đo trực tiếp (QoS 0), trạng thái đèn và ngưỡng; không nhận tổng đếm từ mạch.
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection rejected: %s", reason_code)
            return
        topics = [(self.settings.sensor_topic, 0), ("esp32/status", 1)]
        topics += [(f"esp32/{led}/status", 1) for led in self.settings.device_map.values()]
        topics += [(f"esp32/thresholds/{key}/status", 1) for key in SENSOR_KEYS]
        client.subscribe(topics)
        log.info("MQTT connected; subscribed to %s", topics)

    # Khi mất broker, trạng thái online của ESP32 trở về chưa xác định.
    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.esp_online = None

    # Trả trạng thái broker/ESP32; quá 20 giây không có hoạt động thì coi ESP32 offline.
    def connection_status(self):
        connected = bool(self.settings.mqtt_enabled and self.client.is_connected())
        if connected:
            online = self.esp_online
        else:
            online = None
        if online and self.last_seen is not None and monotonic() - self.last_seen > ESP32_OFFLINE_TIMEOUT_SECONDS:
            online = False
        return {"mqttConnected": connected, "esp32Online": online}

    # Giải mã payload MQTT thành chuỗi rồi chuyển tới handle_message; ghi log nếu dữ liệu lỗi.
    def _on_message(self, client, userdata, message):
        try:
            self.handle_message(message.topic, message.payload.decode("utf-8"), bool(message.retain))
        except Exception:
            log.exception("Invalid MQTT message on %s", message.topic)

    # Chỉ số đo trực tiếp mới tạo cảnh báo; bỏ qua retained và tổng đếm của firmware cũ.
    def handle_message(self, topic, payload, retained=False):
        with self.lock:
            if topic == self.settings.sensor_topic:
                if not retained:
                    self._sensor_data(payload)
            elif topic == "esp32/status":
                self.esp_online = "STATUS: ONLINE" in payload
                self.last_seen = monotonic()
                self.hub.emit("/topic/esp32-status", {"message": payload})
            elif topic.startswith("esp32/thresholds/") and topic.endswith("/status"):
                key = topic.split("/")[2]
                limits = {"temperature": 50, "humidity": 100, "light": 4095}
                if key in SENSOR_KEYS:
                    value = float(payload)
                    if math.isfinite(value) and 0 <= value <= limits[key]:
                        if key in self.threshold_pending and not math.isclose(value, self.thresholds[key], abs_tol=0.0006):
                            return
                        self.thresholds[key] = value
                        self.threshold_confirmed[key] = True
                        self.applied_thresholds[key] = value
                        self.threshold_pending.discard(key)
                        self.hub.emit("/topic/thresholds", self.threshold_status())
            else:
                for device_id, led in self.settings.device_map.items():
                    if topic == f"esp32/{led}/status":
                        self._device_status(device_id, payload.strip(), retained)
                        break

    # Lưu số đo, lịch sử cảnh báo và tổng trong cùng transaction; chỉ phát sự kiện sau commit.
    def _sensor_data(self, payload):
        values = json.loads(payload)
        if not isinstance(values, dict):
            raise ValueError("Sensor payload must be a JSON object")
        clean = {}
        recorded_at = now()
        new_history = False
        with self.sessions.begin() as db:
            for key in SENSOR_KEYS:
                value = values.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    continue
                sensor = execute_sql(db, """
                    SELECT id FROM sensors
                    WHERE mqtt_key = :mqtt_key OR type = :sensor_type LIMIT 1
                """, {'mqtt_key': key, 'sensor_type': key.upper()}).mappings().first()
                if sensor:
                    execute_sql(db, """
                        INSERT INTO datasensors (sensor_id, value, recorded_at)
                        VALUES (:sensor_id, :value, :recorded_at)
                    """, {'sensor_id': sensor['id'], 'value': float(value), 'recorded_at': recorded_at})
                    threshold = self._sample_threshold(values, key)
                    if threshold is not None and value > threshold:
                        led = SENSOR_LEDS[key]
                        device_id = next((device_id for device_id, mapped_led in self.settings.device_map.items()
                                          if mapped_led == led), None)
                        if device_id is not None and execute_sql(
                            db, 'SELECT id FROM devices WHERE id = :id', {'id': device_id}
                        ).first():
                            self._record_alert(db, led, device_id, float(value), threshold, recorded_at)
                            new_history = True
                clean[key] = value
        if isinstance(values.get("error"), str):
            clean["error"] = values["error"]
        if clean:
            self.esp_online = True
            self.last_seen = monotonic()
            self.hub.emit("/topic/sensors", clean, recorded_at=date_string(recorded_at))
        if new_history:
            self.hub.emit("/topic/alert-counts", self.alert_counts_status())
            self.hub.emit("/topic/history", {"action": "ALERT"})

    # Firmware mới gửi ngưỡng cùng mẫu; firmware cũ dùng ngưỡng /status đã xác nhận.
    # Không suy ra cảnh báo từ ngưỡng mặc định chưa biết hoặc ngưỡng mới chỉ vừa gửi đi.
    def _sample_threshold(self, values, key):
        if 'thresholds' in values:
            thresholds = values['thresholds']
            if not isinstance(thresholds, dict):
                return None
            threshold = thresholds.get(key)
        else:
            threshold = self.applied_thresholds[key]
        if (type(threshold) not in (int, float) or not math.isfinite(threshold)
                or not 0 <= threshold <= THRESHOLD_LIMITS[key]):
            return None
        return float(threshold)

    # Mỗi mẫu vượt ngưỡng tạo đúng một history và cộng 1. Mọi thao tác dùng cùng db transaction.
    # Bất kỳ INSERT/UPDATE nào lỗi thì cả số đo, history và count đều rollback.
    def _record_alert(self, db, led, device_id, value, threshold, recorded_at):
        params = {'led': led, 'updated_at': recorded_at}
        if db.bind.dialect.name == 'mysql':
            sql = """INSERT INTO alert_counts (led, total, updated_at)
                     VALUES (:led, 1, :updated_at)
                     ON DUPLICATE KEY UPDATE total = total + 1, updated_at = VALUES(updated_at)"""
        else:
            sql = """INSERT INTO alert_counts (led, total, updated_at)
                     VALUES (:led, 1, :updated_at)
                     ON CONFLICT(led) DO UPDATE SET total = alert_counts.total + 1,
                                                   updated_at = excluded.updated_at"""
        execute_sql(db, sql, params)
        total = execute_sql(db, 'SELECT total FROM alert_counts WHERE led = :led', {'led': led}).scalar_one()
        result = execute_sql(db, """
            INSERT INTO histories (device_id, user_id, action, status, timestamp)
            VALUES (:device_id, NULL, 'ALERT', 'RECORDED', :timestamp)
        """, {'device_id': device_id, 'timestamp': recorded_at})
        execute_sql(db, """
            INSERT INTO alert_history_details
                (history_id, occurrence_count, total, trigger_value, trigger_threshold)
            VALUES (:history_id, 1, :total, :value, :threshold)
        """, {'history_id': result.lastrowid, 'total': total, 'value': value, 'threshold': threshold})

    # Đọc tổng đã commit từ DB; chưa có cảnh báo nào thì trả 0.
    def alert_counts_status(self):
        with self.lock, self.sessions() as db:
            rows = execute_sql(db, 'SELECT led, total FROM alert_counts').mappings().all()
            counts = {row['led']: row['total'] for row in rows}
            return {device_id: counts.get(led, 0) for device_id, led in self.settings.device_map.items()}

    # Trả bản sao các ngưỡng và cờ confirmed để API/WebSocket dùng cùng cấu trúc.
    def threshold_status(self):
        with self.lock:
            return {"values": dict(self.thresholds), "confirmed": dict(self.threshold_confirmed)}

    # Nhận dictionary ba ngưỡng, publish từng giá trị retained qua MQTT và đánh dấu chờ ACK.
    # Publish thành công chỉ là gửi lệnh; phải nhận /status phù hợp mới xác nhận ESP32 đã áp dụng.
    def set_thresholds(self, values):
        with self.lock:
            if not self.settings.mqtt_enabled or not self.client.is_connected():
                raise ControlError("MQTT broker chưa kết nối", 503)
            # Gửi từng ngưỡng riêng; retain giữ giá trị cuối ở broker, QoS 1 có thể gửi lặp.
            for key, value in values.items():
                result = self.client.publish(f"esp32/thresholds/{key}/control", str(value), qos=1, retain=True)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise ControlError("Không gửi được cấu hình ngưỡng MQTT", 503)
                self.thresholds[key] = value
                # Chờ ESP32 gửi giá trị phù hợp qua /status mới coi là đã áp dụng.
                self.threshold_confirmed[key] = False
                self.threshold_pending.add(key)
            self.hub.emit("/topic/thresholds", self.threshold_status())
            # Trả cho HTTP request; hub.emit phía trên thông báo riêng qua WebSocket.
            return self.threshold_status()

    # Xử lý ON/OFF/FAIL từ ESP32, cập nhật thiết bị và history đang chờ nếu ACK phù hợp.
    # Retained chỉ đồng bộ trạng thái, không xác nhận lệnh; FAIL không được hiểu thành OFF.
    def _device_status(self, device_id, payload, retained):
        if payload not in {"ON", "OFF", "FAIL"}:
            return
        self.expire_pending()
        with self.sessions.begin() as db:
            device = execute_sql(db, "SELECT * FROM devices WHERE id = :id",
                                 {'id': device_id}).mappings().first()
            if device is None:
                return
            status, updated_at = device['status'], device['updated_at']
            if payload != "FAIL":
                status, updated_at = int(payload == "ON"), now()
                execute_sql(db, """
                    UPDATE devices SET status = :status, updated_at = :updated_at WHERE id = :id
                """, {'status': status, 'updated_at': updated_at, 'id': device_id})
            # Retained snapshots update device state, but do not acknowledge commands.
            if retained:
                pending = None
            else:
                pending = execute_sql(db, """
                    SELECT id, action FROM histories
                    WHERE device_id = :device_id AND status = 'PENDING'
                    ORDER BY id DESC LIMIT 1
                """, {'device_id': device_id}).mappings().first()
            if pending and (payload == "FAIL" or pending['action'] == payload):
                if payload == 'FAIL':
                    history_status = 'FAILED'
                else:
                    history_status = 'SUCCESS'
                execute_sql(db, "UPDATE histories SET status = :status WHERE id = :id",
                            {'status': history_status, 'id': pending['id']})
            data = {"deviceId": device_id, "status": status,
                    "timestamp": date_string(updated_at), "result": payload}
        self.hub.emit("/topic/device-status", data)

    # Kiểm tra thiết bị, broker và lệnh đang chờ; lưu history PENDING trước khi publish ON/OFF.
    def control(self, device_id, status, user_id):
        with self.lock:
            self.expire_pending()
            with self.sessions.begin() as db:
                device = execute_sql(db, "SELECT * FROM devices WHERE id = :id",
                                     {'id': device_id}).mappings().first()
                if device is None:
                    raise ControlError("Không tìm thấy thiết bị", 404)
                led = self.settings.device_map.get(device_id)
                if led is None:
                    raise ControlError("Thiết bị chưa được ánh xạ trong MQTT_DEVICE_MAP", 400)
                if not self.settings.mqtt_enabled or not self.client.is_connected():
                    raise ControlError("MQTT broker chưa kết nối", 503)
                pending = execute_sql(db, """
                    SELECT id FROM histories
                    WHERE device_id = :device_id AND status = 'PENDING' LIMIT 1
                """, {'device_id': device_id}).first()
                if pending:
                    raise ControlError("Thiết bị đang chờ phản hồi lệnh trước", 409)
                if status == 1:
                    action = "ON"
                else:
                    action = "OFF"
                result = execute_sql(db, """
                    INSERT INTO histories (device_id, user_id, action, status, timestamp)
                    VALUES (:device_id, :user_id, :action, 'PENDING', :timestamp)
                """, {'device_id': device_id, 'user_id': user_id, 'action': action, 'timestamp': now()})
                history_id = result.lastrowid
            # Commit before publishing so the MQTT callback can find the PENDING row.
            try:
                result = self.client.publish(f"esp32/{led}/control", action, qos=1, retain=False)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"MQTT publish error: {result.rc}")
            except Exception as exc:
                with self.sessions.begin() as db:
                    execute_sql(db, "UPDATE histories SET status = 'FAILED' WHERE id = :id",
                                {'id': history_id})
                raise ControlError("Không gửi được lệnh MQTT", 503) from exc

    # Tìm lệnh PENDING quá timeout, chuyển FAILED rồi phát TIMEOUT cho frontend.
    def expire_pending(self):
        events = []
        with self.lock, self.sessions.begin() as db:
            cutoff = now() - timedelta(seconds=self.settings.command_timeout)
            rows = execute_sql(db, """
                SELECT h.id, h.device_id, d.status AS device_status
                FROM histories AS h
                LEFT JOIN devices AS d ON d.id = h.device_id
                WHERE h.status = 'PENDING' AND h.timestamp < :cutoff
            """, {'cutoff': cutoff}).mappings().all()
            for row in rows:
                execute_sql(db, "UPDATE histories SET status = 'FAILED' WHERE id = :id", {'id': row['id']})
                events.append({"deviceId": row['device_id'], "status": row['device_status'],
                               "timestamp": date_string(now()), "result": "TIMEOUT"})
        for event in events:
            self.hub.emit("/topic/device-status", event)
