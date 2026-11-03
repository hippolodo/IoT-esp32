"""Control history using parameterized SQL."""
from datetime import datetime
from sqlalchemy.orm import Session
from ..contracts import history_dict, now, paginate, parse_date, time_range


# Ghép lịch sử với thiết bị/chi tiết cảnh báo, áp dụng bộ lọc và thứ tự trước phân trang.
def history_page(
    db: Session, device_id, status, start, end, page, size,
    inclusive=False, action=None, sort='desc',
):
    if sort not in {"asc", "desc"}:
        raise ValueError("sort phải là asc hoặc desc")
    sql = """
        SELECT h.id, h.device_id, h.user_id, h.action, h.status, h.timestamp,
               d.name AS device_name, a.occurrence_count AS alert_count, a.total AS alert_total,
               a.trigger_value, a.trigger_threshold
        FROM histories AS h
        LEFT JOIN devices AS d ON d.id = h.device_id
        LEFT JOIN alert_history_details AS a ON a.history_id = h.id
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
        if action not in {"ON", "OFF", "ALERT"}:
            raise ValueError("action phải là ON, OFF hoặc ALERT")
        sql += ' AND h.action = :action'
        params['action'] = action
    if start:
        sql += ' AND h.timestamp >= :start'
        params['start'] = start
    if end:
        if inclusive:
            sql += ' AND h.timestamp <= :end'
        else:
            sql += ' AND h.timestamp < :end'
        params['end'] = end
    # Only the validated ASC/DESC keyword is inserted, never user-supplied SQL.
    direction = sort.upper()
    sql += f' ORDER BY h.timestamp {direction}, h.id {direction}'
    return paginate(db, sql, params, page, size, history_dict)


# Đổi thời gian nhập thành khoảng lọc rồi lấy trang lịch sử ON/OFF/ALERT.
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
):
    start, end = time_range(startTime, endTime)
    return history_page(db, deviceId, status, start, end, page, size, action=action, sort=sort)


# Giữ cách lọc API cũ: bắt buộc thiết bị/trạng thái và dùng khoảng thời gian đóng.
def filter_history(
    db: Session, deviceId: int | None = None, status: str | None = None,
    startTime: str | None = None, endTime: str | None = None, page: int = 0, size: int = 10,
):
    if deviceId is None or status is None:
        raise ValueError("deviceId và status không được để trống")
    if startTime:
        start = parse_date(startTime)
    else:
        start = datetime(2000, 1, 1)
    if endTime:
        end = parse_date(endTime)
    else:
        end = now()
    if start > end:
        raise ValueError("startTime phải nhỏ hơn hoặc bằng endTime")
    return history_page(db, deviceId, status, start, end, page, size, inclusive=True)
