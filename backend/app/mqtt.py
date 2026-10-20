import json
import logging
import math
import threading
import uuid
from datetime import timedelta
from time import monotonic

import paho.mqtt.client as mqtt
from sqlalchemy import or_, select

from .contracts import date_string
from .database import DataSensor, Device, History, Sensor, now

log = logging.getLogger(__name__)


class ControlError(Exception):
    def __init__(self, message, code):
        self.message, self.code = message, code


class EventHub:
    """Deliver MQTT thread events to bounded queues on the ASGI event loop."""
    def __init__(self):
        self.loop = None
        self.subscribers = set()

    def emit(self, topic, data):
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._enqueue, {"topic": topic, "data": data})

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
            self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=15)
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
        if online and self.last_seen is not None and monotonic() - self.last_seen > 20:
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
        with self.sessions.begin() as db:
            for key in ("temperature", "humidity", "light"):
                value = values.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    continue
                sensor = db.scalars(select(Sensor).where(or_(
                    Sensor.mqtt_key == key, Sensor.type == key.upper()))).first()
                if sensor:
                    db.add(DataSensor(sensor_id=sensor.id, value=float(value), recorded_at=now()))
                clean[key] = value
        if isinstance(values.get("error"), str):
            clean["error"] = values["error"]
        if clean:
            self.esp_online = True
            self.last_seen = monotonic()
            self.hub.emit("/topic/sensors", clean)

    def _device_status(self, device_id, payload, retained):
        if payload not in {"ON", "OFF", "FAIL"}:
            return
        self.expire_pending()
        with self.sessions.begin() as db:
            device = db.get(Device, device_id)
            if device is None:
                return
            if payload != "FAIL":
                device.status = int(payload == "ON")
                device.updated_at = now()
            # A retained snapshot on subscribe is not a command acknowledgment.
            pending = None if retained else db.scalars(select(History).where(
                History.device_id == device_id, History.status == "PENDING"
            ).order_by(History.id.desc())).first()
            if pending and (payload == "FAIL" or pending.action == payload):
                pending.status = "FAILED" if payload == "FAIL" else "SUCCESS"
            data = {"deviceId": device_id, "status": device.status,
                    "timestamp": date_string(device.updated_at), "result": payload}
        self.hub.emit("/topic/device-status", data)

    def control(self, device_id, status, user_id):
        with self.lock:
            self.expire_pending()
            with self.sessions.begin() as db:
                if db.get(Device, device_id) is None:
                    raise ControlError("Không tìm thấy thiết bị", 404)
                led = self.settings.device_map.get(device_id)
                if led is None:
                    raise ControlError("Thiết bị chưa được ánh xạ trong MQTT_DEVICE_MAP", 400)
                if not self.settings.mqtt_enabled or not self.client.is_connected():
                    raise ControlError("MQTT broker chưa kết nối", 503)
                pending = db.scalars(select(History).where(
                    History.device_id == device_id, History.status == "PENDING")).first()
                if pending:
                    raise ControlError("Thiết bị đang chờ phản hồi lệnh trước", 409)
                action = "ON" if status == 1 else "OFF"
                history = History(device_id=device_id, user_id=user_id, action=action, status="PENDING", timestamp=now())
                db.add(history)
                db.flush()
                history_id = history.id
            # Commit before publishing so the callback can find its pending row.
            try:
                result = self.client.publish(f"esp32/{led}/control", action, qos=1, retain=False)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"MQTT publish error: {result.rc}")
            except Exception as exc:
                with self.sessions.begin() as db:
                    db.get(History, history_id).status = "FAILED"
                raise ControlError("Không gửi được lệnh MQTT", 503) from exc

    def expire_pending(self):
        with self.lock, self.sessions.begin() as db:
            cutoff = now() - timedelta(seconds=self.settings.command_timeout)
            rows = db.scalars(select(History).where(History.status == "PENDING", History.timestamp < cutoff)).all()
            for row in rows:
                row.status = "FAILED"
                self.hub.emit("/topic/device-status", {"deviceId": row.device_id,
                              "status": row.device.status if row.device else None,
                              "timestamp": date_string(now()), "result": "TIMEOUT"})
