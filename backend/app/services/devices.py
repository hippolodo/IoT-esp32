"""Device queries and the HTTP control entry point."""
from sqlalchemy.orm import Session
from ..contracts import ControlError, device_dict, execute_sql
from ..schemas import DeviceControlRequest
from .mqtt import MqttService


def device_response(row, db: Session, settings):
    result = device_dict(row)
    led = settings.device_map.get(row['id']) if row['device_type'] != "WIND_WARNING" else None
    result["controllable"] = led is not None
    result["controlPin"] = {"led1": 2, "led2": 5}.get(led)
    result["pending"] = execute_sql(db, """
        SELECT id FROM histories
        WHERE device_id = :device_id AND status = 'PENDING' LIMIT 1
    """, {'device_id': row['id']}).first() is not None
    return result


def devices(db: Session, settings):
    rows = execute_sql(db, "SELECT * FROM devices ORDER BY id ASC").mappings().all()
    return [device_response(row, db, settings) for row in rows]


def control(body: DeviceControlRequest, user: dict, mqtt: MqttService):
    if body.status not in (0, 1):
        raise ControlError("Status phải là 0 (OFF) hoặc 1 (ON)", 400)
    mqtt.control(body.deviceId, body.status, user_id=user['id'])
    # Device state changes only after the ESP32 acknowledgment.
    return "OK"


def device(id: int, db: Session, settings):
    row = execute_sql(db, "SELECT * FROM devices WHERE id = :id", {'id': id}).mappings().first()
    if row is None:
        raise ControlError("Không tìm thấy thiết bị", 404)
    return device_response(row, db, settings)
