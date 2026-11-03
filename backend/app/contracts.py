import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import DateTime, bindparam, text
from starlette.exceptions import HTTPException

log = logging.getLogger(__name__)


class ControlError(Exception):
    # Gói thông báo và mã HTTP của lỗi nghiệp vụ để exception handler trả về client.
    def __init__(self, message, code):
        self.message, self.code = message, code


# Lấy giờ Việt Nam và bỏ thông tin timezone để tương thích các cột datetime hiện có.
def now():
    # Keep database timestamps in Vietnam local time, regardless of host timezone.
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)


# Đóng gói kết quả API theo cấu trúc success/message/data/code mà frontend đang đọc.
def envelope(data=None, message="OK", code=200):
    return {"success": code < 400, "message": message, "data": data, "code": code}


# Đăng ký cách chuyển các loại lỗi thành JSON response thống nhất.
def register_exception_handlers(app):
    # Đổi lỗi kiểm tra request của FastAPI/Pydantic thành HTTP 400.
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(envelope(message="Dữ liệu đầu vào không hợp lệ", code=400), status_code=400)

    # Trả HTTP 400 cho lỗi giá trị như định dạng thời gian hoặc phân trang.
    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse(envelope(message=str(exc), code=400), status_code=400)

    # Trả đúng thông báo và mã HTTP do nghiệp vụ chủ động phát sinh.
    @app.exception_handler(ControlError)
    async def control_error(request, exc):
        return JSONResponse(envelope(message=exc.message, code=exc.code), status_code=exc.code)

    # Đóng gói HTTPException theo cùng cấu trúc response của dự án.
    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(envelope(message=str(exc.detail), code=exc.status_code), status_code=exc.status_code)

    # Ghi chi tiết lỗi vào log, chỉ trả thông báo chung HTTP 500 cho client.
    @app.exception_handler(Exception)
    async def server_error(request, exc):
        log.error("Request failed: %s", request.url.path, exc_info=exc)
        return JSONResponse(envelope(message="Lỗi hệ thống", code=500), status_code=500)


# Chuẩn hóa datetime: MySQL thường trả object, truy vấn SQLite có thể trả chuỗi.
def as_datetime(value):
    # MySQL returns datetime objects; SQLite text queries can return strings.
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    else:
        return value


# Định dạng thời gian thành yyyy-MM-dd HH:mm:ss; thiếu dữ liệu thì trả N/A.
def date_string(value):
    if value:
        return as_datetime(value).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return "N/A"


# Chạy SQL có tham số qua Session; gắn kiểu datetime để MySQL/SQLite hiểu nhất quán.
def execute_sql(db, sql, params=None):
    """Execute parameterized SQL; preserve datetime binding on MySQL and SQLite."""
    params = params or {}
    statement = text(sql)
    for name, value in params.items():
        if isinstance(value, datetime):
            statement = statement.bindparams(bindparam(name, type_=DateTime))
    return db.execute(statement, params)


# Tạo dictionary thiết bị cho API, đổi tên cột snake_case sang trường camelCase.
def device_dict(row):
    return dict(id=row['id'], name=row['name'], type=row['device_type'], pinGpio=row['pin_gpio'],
                status=row['status'], updatedAt=date_string(row['updated_at']))


# Chuyển dòng danh mục cảm biến thành dictionary có tên trường frontend sử dụng.
def sensor_dict(row):
    return dict(id=row['id'], name=row['name'], type=row['type'], unit=row['unit'], pinGpio=row['pin_gpio'],
                mqttKey=row['mqtt_key'], module=row['module'])


# Chuyển một dòng số đo SQL thành dữ liệu API: sensorType, value, recordedAt...
# Đổi tên trường trong kết quả trả về, không đổi tên cột của database.
def data_dict(row):
    return dict(id=row['id'], sensorId=row['sensor_id'], sensorName=row['sensor_name'], sensorType=row['sensor_type'],
                unit=row['unit'], value=row['value'], recordedAt=date_string(row['recorded_at']))


# Chuyển dòng lịch sử kèm chi tiết cảnh báo thành dictionary trả cho frontend.
def history_dict(row):
    return dict(id=row['id'], userId=row['user_id'], deviceId=row['device_id'], deviceName=row['device_name'],
                action=row['action'], status=row['status'], timestamp=date_string(row['timestamp']),
                alertCount=row['alert_count'], alertTotal=row['alert_total'],
                alertValue=row['trigger_value'], alertThreshold=row['trigger_threshold'])


# Đọc chuỗi thời gian theo độ chính xác ngày/giờ/phút/giây; sai định dạng thì báo lỗi.
def parse_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}(:\d{2}(:\d{2})?)?)?", value):
        raise ValueError("Thời gian phải theo yyyy-MM-dd, yyyy-MM-dd HH, yyyy-MM-dd HH:mm hoặc yyyy-MM-dd HH:mm:ss")
    formats = {10: "%Y-%m-%d", 13: "%Y-%m-%d %H", 16: "%Y-%m-%d %H:%M", 19: "%Y-%m-%d %H:%M:%S"}
    try:
        return datetime.strptime(value, formats[len(value)])
    except ValueError:
        raise ValueError("Định dạng thời gian không hợp lệ") from None


# Tạo khoảng [start, end) và mở rộng end để bao gồm toàn bộ đơn vị thời gian cuối.
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


# Đếm tổng bản ghi rồi lấy một trang bằng LIMIT/OFFSET, chuyển mỗi dòng qua serialize.
def paginate(db, query_sql, params, page, size, serialize):
    if page < 0 or size <= 0:
        raise ValueError("page phải lớn hơn hoặc bằng 0 và size phải lớn hơn 0")
    total = execute_sql(db, f"SELECT COUNT(*) FROM ({query_sql}) AS page_rows", params).scalar_one()
    rows = execute_sql(db, query_sql + " LIMIT :_limit OFFSET :_offset",
                       {**params, '_limit': size, '_offset': page * size}).mappings().all()
    content = [serialize(row) for row in rows]
    pages = (total + size - 1) // size
    sort = {"empty": False, "sorted": True, "unsorted": False}
    return {"content": content, "pageable": {"pageNumber": page, "pageSize": size,
            "sort": sort, "offset": page * size, "paged": True, "unpaged": False},
            "totalPages": pages, "totalElements": total, "last": page >= pages - 1,
            "size": size, "number": page, "sort": sort, "numberOfElements": len(content),
            "first": page == 0, "empty": not content}
