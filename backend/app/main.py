import asyncio
import hashlib
import hmac
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime

import anyio
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from .config import Settings
from .contracts import (data_dict, device_dict, envelope, history_dict, paginate,
                        parse_date, sensor_dict, time_range)
from .database import Base, DataSensor, Device, History, Sensor, User, make_database, now, seed_database
from .mqtt import ControlError, EventHub, MqttService

log = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class DeviceControlRequest(BaseModel):
    deviceId: StrictInt
    status: StrictInt


def create_app(settings=None):
    settings = settings or Settings()
    engine, sessions = make_database(settings.database_url)
    hub = EventHub()
    mqtt = MqttService(settings, sessions, hub)

    async def expire_commands():
        while True:
            await asyncio.sleep(1)
            try:
                await asyncio.to_thread(mqtt.expire_pending)
            except Exception:
                log.exception("Failed to expire pending commands")

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        seed_database(sessions)
        hub.loop = asyncio.get_running_loop()
        mqtt.start()
        task = asyncio.create_task(expire_commands())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await asyncio.to_thread(mqtt.stop)
            hub.loop = None
            engine.dispose()

    app = FastAPI(title="IoT ESP32 Backend", version="1.0.0", lifespan=lifespan)
    app.state.sessions, app.state.mqtt, app.state.hub = sessions, mqtt, hub
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    def database():
        with sessions() as db:
            yield db

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(envelope(message="Dữ liệu đầu vào không hợp lệ", code=400), status_code=400)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse(envelope(message=str(exc), code=400), status_code=400)

    @app.exception_handler(ControlError)
    async def control_error(request, exc):
        return JSONResponse(envelope(message=exc.message, code=exc.code), status_code=exc.code)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(envelope(message=str(exc.detail), code=exc.status_code), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def server_error(request, exc):
        log.error("Request failed: %s", request.url.path, exc_info=exc)
        return JSONResponse(envelope(message="Lỗi hệ thống", code=500), status_code=500)

    @app.get("/api/auth/health")
    def health():
        return envelope("OK", "Backend đang chạy")

    @app.post("/api/auth/login")
    def login(body: LoginRequest, db: Session = Depends(database)):
        if not body.username:
            raise ControlError("Username không được để trống", 400)
        if not body.password:
            raise ControlError("Password không được để trống", 400)
        user = db.scalars(select(User).where(User.username == body.username)).first()
        hashed = hashlib.sha256(body.password.encode()).hexdigest()
        if not user or not hmac.compare_digest(user.password_hash, hashed):
            raise ControlError("Sai tài khoản hoặc mật khẩu", 401)
        return envelope(dict(userId=user.id, username=user.username, fullName=user.full_name,
                             email=user.email, success=True, message="Đăng nhập thành công"), "Đăng nhập thành công")

    @app.get("/api/user/profile")
    def profile(db: Session = Depends(database)):
        user = db.scalars(select(User).where(User.username == "admin")).first()
        if not user:
            raise ControlError("Không tìm thấy user", 404)
        # Do not expose passwordHash, even though the former entity serializer did.
        return envelope(dict(id=user.id, username=user.username, fullName=user.full_name,
                             email=user.email, createdAt=user.created_at.isoformat() if user.created_at else None),
                        "Lấy thông tin user thành công")

    @app.get("/api/devices")
    def devices(db: Session = Depends(database)):
        return envelope([device_dict(d) for d in db.scalars(select(Device).order_by(Device.id))],
                        "Lấy danh sách thiết bị thành công")

    @app.post("/api/devices/control")
    def control(body: DeviceControlRequest):
        if body.status not in (0, 1):
            raise ControlError("Status phải là 0 (OFF) hoặc 1 (ON)", 400)
        mqtt.control(body.deviceId, body.status)
        # Preserve the legacy response; state remains unchanged until the ESP32 ACK.
        return envelope("OK", "Bật thiết bị thành công" if body.status else "Tắt thiết bị thành công")

    @app.get("/api/devices/{id}")
    def device(id: int, db: Session = Depends(database)):
        row = db.get(Device, id)
        if row is None:
            raise ControlError("Không tìm thấy thiết bị", 404)
        return envelope(device_dict(row), "Lấy thông tin thiết bị thành công")

    @app.get("/api/sensors")
    def sensors(db: Session = Depends(database)):
        return envelope([sensor_dict(s) for s in db.scalars(select(Sensor).order_by(Sensor.id))],
                        "Lấy danh sách cảm biến thành công")

    @app.get("/api/sensors/latest")
    def latest(db: Session = Depends(database)):
        rows = []
        for sensor_id in db.scalars(select(Sensor.id)):
            row = db.scalars(select(DataSensor).where(DataSensor.sensor_id == sensor_id).order_by(
                DataSensor.recorded_at.desc(), DataSensor.id.desc()).limit(1)).first()
            if row:
                rows.append(row)
        rows.sort(key=lambda r: (r.recorded_at or datetime.min, r.id), reverse=True)
        return envelope([data_dict(r) for r in rows], "Lấy dữ liệu cảm biến gần đây thành công")

    @app.get("/api/sensors/data")
    def sensor_data(sensorId: int | None = None, startTime: str | None = None, endTime: str | None = None,
                    page: int = 0, size: int = 10, db: Session = Depends(database)):
        start, end = time_range(startTime, endTime)
        query = select(DataSensor)
        if sensorId is not None:
            query = query.where(DataSensor.sensor_id == sensorId)
        if start:
            query = query.where(DataSensor.recorded_at >= start, DataSensor.recorded_at < end)
        query = query.order_by(DataSensor.recorded_at.desc(), DataSensor.id.desc())
        return envelope(paginate(db, query, page, size, data_dict), "Lấy dữ liệu cảm biến thành công")

    @app.get("/api/sensors/filter")
    def filter_sensors(type: str, startDate: str, endDate: str, page: int = 0, size: int = 10,
                       db: Session = Depends(database)):
        start, end = parse_date(startDate), parse_date(endDate)
        if start > end:
            raise ValueError("startDate phải nhỏ hơn hoặc bằng endDate")
        query = select(DataSensor).join(DataSensor.sensor).where(
            Sensor.type == type, DataSensor.recorded_at >= start, DataSensor.recorded_at <= end
        ).order_by(DataSensor.recorded_at.desc(), DataSensor.id.desc())
        return envelope(paginate(db, query, page, size, data_dict), "Lọc dữ liệu cảm biến thành công")

    def history_page(db, device_id, status, start, end, page, size, inclusive=False):
        query = select(History)
        if device_id is not None:
            query = query.where(History.device_id == device_id)
        if status is not None:
            query = query.where(History.status == status)
        if start:
            query = query.where(History.timestamp >= start)
        if end:
            query = query.where(History.timestamp <= end if inclusive else History.timestamp < end)
        query = query.order_by(History.timestamp.desc(), History.id.desc())
        return paginate(db, query, page, size, history_dict)

    @app.get("/api/history")
    def history(deviceId: int | None = None, status: str | None = None, startTime: str | None = None,
                endTime: str | None = None, page: int = 0, size: int = 10, db: Session = Depends(database)):
        start, end = time_range(startTime, endTime)
        return envelope(history_page(db, deviceId, status, start, end, page, size), "Lấy lịch sử thành công")

    @app.get("/api/history/filter")
    def filter_history(deviceId: int | None = None, status: str | None = None, startTime: str | None = None,
                       endTime: str | None = None, page: int = 0, size: int = 10, db: Session = Depends(database)):
        if deviceId is None or status is None:
            raise ValueError("deviceId và status không được để trống")
        start = parse_date(startTime) if startTime else datetime(2000, 1, 1)
        end = parse_date(endTime) if endTime else now()
        if start > end:
            raise ValueError("startTime phải nhỏ hơn hoặc bằng endTime")
        return envelope(history_page(db, deviceId, status, start, end, page, size, inclusive=True), "Lọc lịch sử thành công")

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        origin = ws.headers.get("origin")
        if origin and origin not in settings.cors_origins:
            await ws.close(code=1008)
            return
        await ws.accept()
        queue = asyncio.Queue(maxsize=100)
        hub.subscribers.add(queue)

        async def send_events():
            while True:
                event = await queue.get()
                if ws.query_params.get("topic") in (None, event["topic"]):
                    await ws.send_json(event)

        async def receive_events():
            while True:
                await ws.receive_text()

        try:
            async with anyio.create_task_group() as group:
                group.start_soon(send_events)
                try:
                    await receive_events()
                except WebSocketDisconnect:
                    pass
                finally:
                    group.cancel_scope.cancel()
        finally:
            hub.subscribers.discard(queue)

    return app


app = create_app()
