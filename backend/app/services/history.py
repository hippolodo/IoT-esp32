"""Control history and wind-warning history using parameterized SQL."""
from datetime import datetime
from sqlalchemy.orm import Session
from ..contracts import date_string, history_dict, now, paginate, parse_date, time_range


def history_page(
    db: Session, device_id, status, start, end, page, size,
    inclusive=False, action=None, sort='desc',
):
    if sort not in {"asc", "desc"}:
        raise ValueError("sort phải là asc hoặc desc")
    sql = """
        SELECT h.id, h.device_id, h.user_id, h.action, h.status, h.timestamp,
               d.name AS device_name
        FROM histories AS h
        LEFT JOIN devices AS d ON d.id = h.device_id
        WHERE 1 = 1
    """
    params = {}
    if device_id is not None:
        sql += ' AND h.device_id = :device_id'
        params['device_id'] = device_id
    if status is not None:
        sql += ' AND h.status = :status'
        params['status'] = status
    if action:
        if action not in {"ON", "OFF"}:
            raise ValueError("action phải là ON hoặc OFF")
        sql += ' AND h.action = :action'
        params['action'] = action
    if start:
        sql += ' AND h.timestamp >= :start'
        params['start'] = start
    if end:
        sql += ' AND h.timestamp <= :end' if inclusive else ' AND h.timestamp < :end'
        params['end'] = end
    # Only the validated ASC/DESC keyword is inserted, never user-supplied SQL.
    direction = sort.upper()
    sql += f' ORDER BY h.timestamp {direction}, h.id {direction}'
    return paginate(db, sql, params, page, size, history_dict)


def history(
    db: Session,
    deviceId: int | None = None,
    status: str | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    page: int = 0,
    size: int = 10,
    action: str | None = None,
    sort: str = 'desc',
    deviceType: str | None = None,
):
    start, end = time_range(startTime, endTime)
    if deviceType is not None:
        if deviceType != "WIND_WARNING" or deviceId is not None:
            raise ValueError("deviceType phải là WIND_WARNING và không đi kèm deviceId")
        if sort not in {"asc", "desc"}:
            raise ValueError("sort phải là asc hoặc desc")
        if action and action not in {"ON", "OFF", "ALERT"}:
            raise ValueError("action phải là ON, OFF hoặc ALERT")
        sql = 'SELECT id, speed, recorded_at FROM WindSpeed WHERE 1 = 1'
        params = {}
        if (status and status != "RECORDED") or (action and action != "ALERT"):
            sql += ' AND 1 = 0'
        if start:
            sql += ' AND recorded_at >= :start AND recorded_at < :end'
            params.update(start=start, end=end)
        direction = sort.upper()
        sql += f' ORDER BY recorded_at {direction}, id {direction}'
        return paginate(db, sql, params, page, size, lambda row: {
            "id": row['id'], "eventType": "WIND_WARNING", "userId": None, "deviceId": None,
            "deviceName": "Đèn cảnh báo", "action": "ALERT", "status": "RECORDED",
            "speed": row['speed'], "timestamp": date_string(row['recorded_at']),
        })
    return history_page(db, deviceId, status, start, end, page, size, action=action, sort=sort)


def filter_history(
    db: Session, deviceId: int | None = None, status: str | None = None,
    startTime: str | None = None, endTime: str | None = None, page: int = 0, size: int = 10,
):
    if deviceId is None or status is None:
        raise ValueError("deviceId và status không được để trống")
    start = parse_date(startTime) if startTime else datetime(2000, 1, 1)
    end = parse_date(endTime) if endTime else now()
    if start > end:
        raise ValueError("startTime phải nhỏ hơn hoặc bằng endTime")
    return history_page(db, deviceId, status, start, end, page, size, inclusive=True)
