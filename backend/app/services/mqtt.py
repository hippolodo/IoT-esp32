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
        self.thresholds = dict(temperature=35.0, humidity=80.0, light=3000.0)
        self.threshold_confirmed = {key: False for key in SENSOR_KEYS}
        self.threshold_pending = set()
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
        topics = [(self.settings.sensor_topic, 1), ("esp32/status", 1), ("esp32/leds/alert-counts", 1)]
        topics += [(f"esp32/{led}/status", 1) for led in self.settings.device_map.values()]
        topics += [(f"esp32/thresholds/{key}/status", 1) for key in SENSOR_KEYS]
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
            elif topic == "esp32/leds/alert-counts":
                counts = json.loads(payload)
                if not isinstance(counts, dict) or any(
                    type(counts.get(led)) is not int or not 0 <= counts[led] <= 4294967295
                    for led in ("led1", "led2", "led3")
                ):
                    raise ValueError("Invalid LED alert counts")
                # Store cumulative snapshots, never add them or lower a saved total.
                # Dialect upserts also prevent duplicate rows from concurrent callbacks.
                new_history = False
                with self.sessions.begin() as db:
                    dialect = db.bind.dialect.name
                    for led in ("led1", "led2", "led3"):
                        previous = execute_sql(db, 'SELECT total FROM alert_counts WHERE led = :led'
                                               + (' FOR UPDATE' if dialect == 'mysql' else ''),
                                               {'led': led}).scalar_one_or_none()
                        params = {'led': led, 'total': counts[led], 'updated_at': now()}
                        if dialect == 'mysql':
                            sql = """INSERT INTO alert_counts (led, total, updated_at)
                                     VALUES (:led, :total, :updated_at)
                                     ON DUPLICATE KEY UPDATE
                                     updated_at = IF(VALUES(total) > total, VALUES(updated_at), updated_at),
                                     total = GREATEST(total, VALUES(total))"""
                        else:
                            sql = """INSERT INTO alert_counts (led, total, updated_at)
                                     VALUES (:led, :total, :updated_at)
                                     ON CONFLICT(led) DO UPDATE SET
                                     total = excluded.total, updated_at = excluded.updated_at
                                     WHERE excluded.total > alert_counts.total"""
                        execute_sql(db, sql, params)
                        device_id = next((key for key, value in self.settings.device_map.items() if value == led), None)
                        device_exists = device_id is not None and execute_sql(
                            db, 'SELECT id FROM devices WHERE id = :id', {'id': device_id}).first()
                        # A first snapshot can describe its last known episode, but not older ones.
                        detail = counts.get('details', {})
                        detail = detail.get(led) if isinstance(detail, dict) else None
                        value = threshold = None
                        limits = {'led1': 50, 'led2': 100, 'led3': 4095}
                        if isinstance(detail, dict):
                            v, t = detail.get('value'), detail.get('threshold')
                            if (type(detail.get('total')) is int and detail['total'] == counts[led]
                                and type(v) in (int, float) and type(t) in (int, float)
                                and math.isfinite(v) and math.isfinite(t) and v > t
                                and 0 <= t <= limits[led]):
                                value, threshold = float(v), float(t)
                        if device_exists and ((previous is not None and counts[led] > previous)
                                              or (previous is None and value is not None)):
                            result = execute_sql(db, """
                                INSERT INTO histories (device_id, user_id, action, status, timestamp)
                                VALUES (:device_id, NULL, 'ALERT', 'RECORDED', :timestamp)
                            """, {'device_id': device_id, 'timestamp': params['updated_at']})
                            execute_sql(db, """
                                INSERT INTO alert_history_details
                                    (history_id, occurrence_count, total, trigger_value, trigger_threshold)
                                VALUES (:history_id, :occurrence_count, :total, :value, :threshold)
                            """, {'history_id': result.lastrowid, 'occurrence_count': counts[led] - previous if previous is not None else 1,
                                  'total': counts[led], 'value': value, 'threshold': threshold})
                            new_history = True
                self.hub.emit("/topic/alert-counts", self.alert_counts_status())
                if new_history:
                    self.hub.emit("/topic/history", {"action": "ALERT"})
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
                        self.threshold_pending.discard(key)
                        self.hub.emit("/topic/thresholds", self.threshold_status())
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
                clean[key] = value
        if isinstance(values.get("error"), str):
            clean["error"] = values["error"]
        if clean:
            self.esp_online = True
            self.last_seen = monotonic()
            self.hub.emit("/topic/sensors", clean, recorded_at=date_string(recorded_at))
    def alert_counts_status(self):
        with self.lock, self.sessions() as db:
            rows = execute_sql(db, 'SELECT led, total FROM alert_counts').mappings().all()
            counts = {row['led']: row['total'] for row in rows}
            return {device_id: counts.get(led) for device_id, led in self.settings.device_map.items()}

    def threshold_status(self):
        with self.lock:
            return {"values": dict(self.thresholds), "confirmed": dict(self.threshold_confirmed)}

    def set_thresholds(self, values):
        with self.lock:
            if not self.settings.mqtt_enabled or not self.client.is_connected():
                raise ControlError("MQTT broker chưa kết nối", 503)
            for key, value in values.items():
                result = self.client.publish(f"esp32/thresholds/{key}/control", str(value), qos=1, retain=True)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise ControlError("Không gửi được cấu hình ngưỡng MQTT", 503)
                self.thresholds[key] = value
                self.threshold_confirmed[key] = False
                self.threshold_pending.add(key)
            self.hub.emit("/topic/thresholds", self.threshold_status())
            return self.threshold_status()

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
