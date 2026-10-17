import re
from datetime import datetime, timedelta

from sqlalchemy import func, select


def envelope(data=None, message="OK", code=200):
    return {"success": code < 400, "message": message, "data": data, "code": code}


def date_string(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else "N/A"


def device_dict(row):
    return dict(id=row.id, name=row.name, pinGpio=row.pin_gpio, status=row.status, updatedAt=date_string(row.updated_at))


def sensor_dict(row):
    return dict(id=row.id, name=row.name, type=row.type, unit=row.unit, pinGpio=row.pin_gpio,
                mqttKey=row.mqtt_key, module=row.module)


def data_dict(row):
    return dict(id=row.id, sensorId=row.sensor_id, sensorName=row.sensor.name, sensorType=row.sensor.type,
                unit=row.sensor.unit, value=row.value, recordedAt=date_string(row.recorded_at))


def history_dict(row):
    return dict(id=row.id, deviceId=row.device_id, deviceName=row.device.name if row.device else None,
                action=row.action, status=row.status, timestamp=date_string(row.timestamp))


def parse_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}(:\d{2}(:\d{2})?)?)?", value):
        raise ValueError("Thời gian phải theo yyyy-MM-dd, yyyy-MM-dd HH, yyyy-MM-dd HH:mm hoặc yyyy-MM-dd HH:mm:ss")
    formats = {10: "%Y-%m-%d", 13: "%Y-%m-%d %H", 16: "%Y-%m-%d %H:%M", 19: "%Y-%m-%d %H:%M:%S"}
    try:
        return datetime.strptime(value, formats[len(value)])
    except ValueError:
        raise ValueError("Định dạng thời gian không hợp lệ") from None


def time_range(start, end):
    start, end = (start or "").strip(), (end or "").strip()
    if not start and not end:
        return None, None
    if not start or not end:
        raise ValueError("startTime và endTime phải được nhập cùng nhau")
    first = parse_date(start)
    last = parse_date(end) + {10: timedelta(days=1), 13: timedelta(hours=1),
                              16: timedelta(minutes=1), 19: timedelta(seconds=1)}[len(end)]
    if first >= last:
        raise ValueError("startTime phải nhỏ hơn hoặc bằng endTime")
    return first, last


def paginate(db, query, page, size, serialize):
    if page < 0 or size <= 0:
        raise ValueError("page phải lớn hơn hoặc bằng 0 và size phải lớn hơn 0")
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    content = [serialize(row) for row in db.scalars(query.offset(page * size).limit(size)).all()]
    pages = (total + size - 1) // size
    sort = {"empty": False, "sorted": True, "unsorted": False}
    return {"content": content, "pageable": {"pageNumber": page, "pageSize": size,
            "sort": sort, "offset": page * size, "paged": True, "unpaged": False},
            "totalPages": pages, "totalElements": total, "last": page >= pages - 1,
            "size": size, "number": page, "sort": sort, "numberOfElements": len(content),
            "first": page == 0, "empty": not content}
