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
SENSOR_KEYS = ("temperature", "humidity", "light", "windSpeed")
WIND_ALERT_THRESHOLD = 300


class EventHub:
    """Deliver MQTT thread events to bounded queues on the ASGI event loop."""
    def __init__(self):
        self.loop = None
        self.subscribers = set()

    def emit(self, topic, data, recorded_at=None):
        if self.loop and not self.loop.is_closed():
            event = {"topic": topic, "data": data}
            if recorded_at is not None:
                event["recordedAt"] = recorded_at
            self.loop.call_soon_threadsafe(self._enqueue, event)

    def _enqueue(self, event):
        for queue in tuple(self.subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)


class MqttService:
    def __init__(self, settings, session_factory, hub):
        self.settings, self.sessions, self.hub = settings, session_factory, hub
        self.lock = threading.RLock()
        self.esp_online = None
        self.last_seen = None
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"iot-python-{uuid.uuid4().hex}")
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def start(self):
        if self.settings.mqtt_enabled:
            self.client.connect_async(
                self.settings.mqtt_host, self.settings.mqtt_port,
                keepalive=MQTT_KEEPALIVE_SECONDS,
            )
            self.client.loop_start()

    def stop(self):
        if self.settings.mqtt_enabled:
            self.client.disconnect()
            self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection rejected: %s", reason_code)
            return
        topics = [(self.settings.sensor_topic, 1), ("esp32/status", 1)]
        topics += [(f"esp32/{led}/status", 1) for led in self.settings.device_map.values()]
        client.subscribe(topics)
        log.info("MQTT connected; subscribed to %s", topics)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.esp_online = None

    def connection_status(self):
        connected = bool(self.settings.mqtt_enabled and self.client.is_connected())
        online = self.esp_online if connected else None
        if online and self.last_seen is not None and monotonic() - self.last_seen > ESP32_OFFLINE_TIMEOUT_SECONDS:
            online = False
        return {"mqttConnected": connected, "esp32Online": online}

    def _on_message(self, client, userdata, message):
        try:
            self.handle_message(message.topic, message.payload.decode("utf-8"), bool(message.retain))
        except Exception:
            log.exception("Invalid MQTT message on %s", message.topic)

    def handle_message(self, topic, payload, retained=False):
        with self.lock:
            if topic == self.settings.sensor_topic:
                self._sensor_data(payload)
            elif topic == "esp32/status":
                self.esp_online = "STATUS: ONLINE" in payload
                self.last_seen = monotonic()
                self.hub.emit("/topic/esp32-status", {"message": payload})
            else:
                for device_id, led in self.settings.device_map.items():
                    if topic == f"esp32/{led}/status":
                        self._device_status(device_id, payload.strip(), retained)
                        break

    def _sensor_data(self, payload):
        values = json.loads(payload)
        if not isinstance(values, dict):
            raise ValueError("Sensor payload must be a JSON object")
        clean = {}
        recorded_at = now()
        new_alert = None
        with self.sessions.begin() as db:
            for key in SENSOR_KEYS:
                value = values.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    continue
                if key == "windSpeed" and not 0 <= value <= 500:
                    continue
                sensor = execute_sql(db, """
                    SELECT id FROM sensors
                    WHERE mqtt_key = :mqtt_key OR type = :sensor_type LIMIT 1
                """, {'mqtt_key': key, 'sensor_type': key.upper()}).mappings().first()
                if sensor:
                    if key == "windSpeed":
                        warning_device = execute_sql(db, """
                            SELECT id FROM devices WHERE device_type = 'WIND_WARNING' LIMIT 1
                        """).mappings().first()
                        if warning_device is not None:
                            execute_sql(db, """
                                UPDATE devices SET status = :status, updated_at = :recorded_at
                                WHERE id = :id
                            """, {'status': int(value > WIND_ALERT_THRESHOLD), 'recorded_at': recorded_at,
                                  'id': warning_device['id']})
                        previous = execute_sql(db, """
                            SELECT value FROM datasensors WHERE sensor_id = :sensor_id
                            ORDER BY recorded_at DESC, id DESC LIMIT 1
                        """, {'sensor_id': sensor['id']}).mappings().first()
                        if value > WIND_ALERT_THRESHOLD and (previous is None or previous['value'] <= WIND_ALERT_THRESHOLD):
                            result = execute_sql(db, """
                                INSERT INTO WindSpeed (sensor_id, speed, recorded_at)
                                VALUES (:sensor_id, :speed, :recorded_at)
                            """, {'sensor_id': sensor['id'], 'speed': float(value), 'recorded_at': recorded_at})
                            new_alert = {'id': result.lastrowid, 'speed': float(value),
                                         'recordedAt': date_string(recorded_at)}
                    execute_sql(db, """
                        INSERT INTO datasensors (sensor_id, value, recorded_at)
                        VALUES (:sensor_id, :value, :recorded_at)
                    """, {'sensor_id': sensor['id'], 'value': float(value), 'recorded_at': recorded_at})
                clean[key] = value
        if isinstance(values.get("error"), str):
            clean["error"] = values["error"]
        if clean:
            self.esp_online = True
            self.last_seen = monotonic()
            self.hub.emit("/topic/sensors", clean, recorded_at=date_string(recorded_at))
        # The transaction above is committed before clients query the new alert.
        if new_alert is not None:
            self.hub.emit("/topic/wind-alerts", new_alert)

    def _device_status(self, device_id, payload, retained):
        if payload not in {"ON", "OFF", "FAIL"}:
            return
        self.expire_pending()
        with self.sessions.begin() as db:
            device = execute_sql(db, "SELECT * FROM devices WHERE id = :id",
                                 {'id': device_id}).mappings().first()
            if device is None or device['device_type'] == "WIND_WARNING":
                return
            status, updated_at = device['status'], device['updated_at']
            if payload != "FAIL":
                status, updated_at = int(payload == "ON"), now()
                execute_sql(db, """
                    UPDATE devices SET status = :status, updated_at = :updated_at WHERE id = :id
                """, {'status': status, 'updated_at': updated_at, 'id': device_id})
            # Retained snapshots update device state, but do not acknowledge commands.
            pending = None if retained else execute_sql(db, """
                SELECT id, action FROM histories
                WHERE device_id = :device_id AND status = 'PENDING'
                ORDER BY id DESC LIMIT 1
            """, {'device_id': device_id}).mappings().first()
            if pending and (payload == "FAIL" or pending['action'] == payload):
                execute_sql(db, "UPDATE histories SET status = :status WHERE id = :id",
                            {'status': 'FAILED' if payload == 'FAIL' else 'SUCCESS', 'id': pending['id']})
            data = {"deviceId": device_id, "status": status,
                    "timestamp": date_string(updated_at), "result": payload}
        self.hub.emit("/topic/device-status", data)

    def control(self, device_id, status, user_id):
        with self.lock:
            self.expire_pending()
            with self.sessions.begin() as db:
                device = execute_sql(db, "SELECT * FROM devices WHERE id = :id",
                                     {'id': device_id}).mappings().first()
                if device is None:
                    raise ControlError("Không tìm thấy thiết bị", 404)
                if device['device_type'] == "WIND_WARNING":
                    raise ControlError("Đèn cảnh báo hoạt động tự động, không nhận lệnh bật/tắt", 400)
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
                action = "ON" if status == 1 else "OFF"
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
