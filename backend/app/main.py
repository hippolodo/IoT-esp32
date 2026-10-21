import asyncio
import hashlib
import logging
import re
import secrets
import threading
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta

import anyio
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, StrictInt
from sqlalchemy import String, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from .config import Settings
from .contracts import (
    data_dict, device_dict, envelope, history_dict, paginate,
    parse_date, sensor_dict, time_range,
)
from .database import (
    AuthSession, DataSensor, Device, History, Sensor, User,
    initialize_database, make_database, now, seed_database,
)
from .mqtt import ControlError, EventHub, MqttService
from .passwords import hash_password, verify_password

log = logging.getLogger(__name__)
SESSION_LIFETIME = timedelta(hours=24)
COMMAND_CHECK_INTERVAL_SECONDS = 1
WEBSOCKET_AUTH_TIMEOUT_SECONDS = 5
WEBSOCKET_SESSION_CHECK_SECONDS = 5
bearer_auth = HTTPBearer(auto_error=False, description="Dán accessToken nhận từ /api/auth/login để xác thực.")


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class RegisterRequest(BaseModel):
    username: str
    fullName: str
    email: str
    password: str
    confirmPassword: str


class DeviceControlRequest(BaseModel):
    deviceId: StrictInt
    status: StrictInt


def create_app(settings=None):
    settings = settings or Settings()
    engine, sessions = make_database(settings.database_url)
    hub = EventHub()
    mqtt = MqttService(settings, sessions, hub)
    registration_lock = threading.Lock()

    async def expire_commands():
        while True:
            await asyncio.sleep(COMMAND_CHECK_INTERVAL_SECONDS)
            try:
                await asyncio.to_thread(mqtt.expire_pending)
            except Exception:
                log.exception("Failed to expire pending commands")

    @asynccontextmanager
    async def lifespan(app):
        initialize_database(engine)
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

    app = FastAPI(
        title="IoT ESP32 Backend", version="1.0.0", lifespan=lifespan,
        openapi_tags=[
            {"name": "Xác thực", "description": "Đăng ký, đăng nhập và đăng xuất tài khoản."},
            {"name": "Người dùng", "description": "Hồ sơ của tài khoản đang đăng nhập."},
            {"name": "Thiết bị", "description": "Danh sách, trạng thái và điều khiển đèn."},
            {"name": "Cảm biến", "description": "Danh mục, số đo mới nhất và tra cứu dữ liệu cảm biến."},
            {"name": "Lịch sử", "description": "Tra cứu và lọc lịch sử điều khiển thiết bị."},
            {"name": "Hệ thống", "description": "Kiểm tra backend và trạng thái kết nối MQTT, ESP32."},
        ],
    )
    app.state.sessions, app.state.mqtt, app.state.hub = sessions, mqtt, hub
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    def database():
        with sessions() as db:
            yield db

    def authenticate_token(token, db):
        session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()) if isinstance(token, str) and token else None
        if session is None or session.expires_at <= now() or db.get(User, session.user_id) is None:
            raise ControlError("Vui lòng đăng nhập để tiếp tục", 401)
        return session

    def current_session(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth),
        db: Session = Depends(database),
    ):
        return authenticate_token(credentials.credentials if credentials else None, db)

    def websocket_session_valid(token):
        with sessions() as db:
            try:
                authenticate_token(token, db)
                return True
            except ControlError:
                return False

    def current_user(session: AuthSession = Depends(current_session), db: Session = Depends(database)):
        return db.get(User, session.user_id)

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

    @app.get("/api/auth/health", tags=["Hệ thống"])
    def health():
        return envelope("OK", "Backend đang chạy")

    @app.get("/api/system/status", tags=["Hệ thống"], dependencies=[Depends(current_session)])
    def system_status():
        return envelope(mqtt.connection_status(), "Trạng thái kết nối")

    def device_response(row, db):
        result = device_dict(row)
        led = settings.device_map.get(row.id)
        result["controllable"] = led is not None
        result["controlPin"] = {"led1": 2, "led2": 5}.get(led)
        result["pending"] = db.scalars(select(History.id).where(
            History.device_id == row.id, History.status == "PENDING")).first() is not None
        return result

    @app.post("/api/auth/register", status_code=201, tags=["Xác thực"])
    def register(body: RegisterRequest, db: Session = Depends(database)):
        username = body.username.strip().lower()
        full_name = body.fullName.strip()
        email = body.email.strip().lower()
        if not re.fullmatch(r"[a-z0-9_.-]{3,50}", username):
            raise ControlError("Tên đăng nhập cần 3–50 ký tự: chữ, số, dấu chấm, gạch dưới hoặc gạch ngang", 400)
        if not full_name or len(full_name) > 255:
            raise ControlError("Họ tên cần từ 1 đến 255 ký tự", 400)
        if len(email) > 255 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ControlError("Email không hợp lệ", 400)
        if not 8 <= len(body.password) <= 128 or not body.password.strip():
            raise ControlError("Mật khẩu cần từ 8 đến 128 ký tự", 400)
        if body.password != body.confirmPassword:
            raise ControlError("Xác nhận mật khẩu không khớp", 400)

        # Serialize registration in the single-worker deployment, including legacy
        # databases whose duplicate rows prevented adding a unique index.
        with registration_lock:
            if db.scalar(select(User.id).where(func.lower(User.username) == username)) is not None:
                raise ControlError("Tên đăng nhập đã được sử dụng", 409)
            if db.scalar(select(User.id).where(func.lower(User.email) == email)) is not None:
                raise ControlError("Email đã được sử dụng", 409)
            user = User(
                username=username, full_name=full_name, email=email,
                password_hash=hash_password(body.password),
            )
            db.add(user)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise ControlError("Tên đăng nhập hoặc email đã được sử dụng", 409) from None
        return envelope(
            dict(userId=user.id, username=user.username, fullName=user.full_name, email=user.email),
            "Đăng ký tài khoản thành công. Vui lòng đăng nhập.", code=201,
        )

    @app.post("/api/auth/login", tags=["Xác thực"])
    def login(body: LoginRequest, db: Session = Depends(database)):
        if not body.username:
            raise ControlError("Username không được để trống", 400)
        if not body.password:
            raise ControlError("Password không được để trống", 400)
        username = body.username.strip().lower()
        user = db.scalars(select(User).where(func.lower(User.username) == username)).first()
        if not user or not verify_password(body.password, user.password_hash):
            raise ControlError("Sai tài khoản hoặc mật khẩu", 401)
        token = secrets.token_urlsafe(32)
        db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                           user_id=user.id, expires_at=now() + SESSION_LIFETIME))
        db.commit()
        return envelope(dict(userId=user.id, username=user.username, fullName=user.full_name, accessToken=token,
                             email=user.email, success=True, message="Đăng nhập thành công"), "Đăng nhập thành công")

    @app.post("/api/auth/logout", tags=["Xác thực"])
    def logout(session: AuthSession = Depends(current_session), db: Session = Depends(database)):
        db.delete(session)
        db.commit()
        return envelope("OK", "Đã đăng xuất")

    @app.get("/api/user/profile", tags=["Người dùng"])
    def profile(user: User = Depends(current_user)):
        return envelope(dict(id=user.id, username=user.username, fullName=user.full_name,
                             email=user.email, createdAt=user.created_at.isoformat() if user.created_at else None),
                        "Lấy thông tin user thành công")

    @app.get("/api/devices", tags=["Thiết bị"], dependencies=[Depends(current_session)])
    def devices(db: Session = Depends(database)):
        return envelope([device_response(d, db) for d in db.scalars(select(Device).order_by(Device.id))],
                        "Lấy danh sách thiết bị thành công")

    @app.post("/api/devices/control", tags=["Thiết bị"])
    def control(body: DeviceControlRequest, user: User = Depends(current_user)):
        if body.status not in (0, 1):
            raise ControlError("Status phải là 0 (OFF) hoặc 1 (ON)", 400)
        mqtt.control(body.deviceId, body.status, user_id=user.id)
        # Device state changes only after the ESP32 acknowledgment.
        return envelope("OK", "Bật thiết bị thành công" if body.status else "Tắt thiết bị thành công")

    @app.get("/api/devices/{id}", tags=["Thiết bị"], dependencies=[Depends(current_session)])
    def device(id: int, db: Session = Depends(database)):
        row = db.get(Device, id)
        if row is None:
            raise ControlError("Không tìm thấy thiết bị", 404)
        return envelope(device_response(row, db), "Lấy thông tin thiết bị thành công")

    @app.get("/api/sensors", tags=["Cảm biến"], dependencies=[Depends(current_session)])
    def sensors(db: Session = Depends(database)):
        return envelope([sensor_dict(s) for s in db.scalars(select(Sensor).order_by(Sensor.id))],
                        "Lấy danh sách cảm biến thành công")

    @app.get("/api/sensors/latest", tags=["Cảm biến"], dependencies=[Depends(current_session)])
    def latest(db: Session = Depends(database)):
        rows = []
        for sensor_id in db.scalars(select(Sensor.id)):
            row = db.scalars(select(DataSensor).where(DataSensor.sensor_id == sensor_id).order_by(
                DataSensor.recorded_at.desc(), DataSensor.id.desc()).limit(1)).first()
            if row:
                rows.append(row)
        rows.sort(key=lambda r: (r.recorded_at or datetime.min, r.id), reverse=True)
        return envelope([data_dict(r) for r in rows], "Lấy dữ liệu cảm biến gần đây thành công")

    @app.get("/api/sensors/data", tags=["Cảm biến"], dependencies=[Depends(current_session)])
    def sensor_data(sensorId: int | None = None, startTime: str | None = None, endTime: str | None = None,
                    page: int = 0, size: int = 10, sensorType: str | None = None,
                    value: str | None = None, db: Session = Depends(database)):
        start, end = time_range(startTime, endTime)
        query = select(DataSensor)
        if sensorId is not None:
            query = query.where(DataSensor.sensor_id == sensorId)
        if sensorType:
            query = query.join(DataSensor.sensor).where(func.upper(Sensor.type) == sensorType.upper())
        if value:
            query = query.where(cast(DataSensor.value, String).contains(value, autoescape=True))
        if start:
            query = query.where(DataSensor.recorded_at >= start, DataSensor.recorded_at < end)
        query = query.order_by(DataSensor.recorded_at.desc(), DataSensor.id.desc())
        return envelope(paginate(db, query, page, size, data_dict), "Lấy dữ liệu cảm biến thành công")

    @app.get("/api/sensors/filter", tags=["Cảm biến"], dependencies=[Depends(current_session)])
    def filter_sensors(type: str, startDate: str, endDate: str, page: int = 0, size: int = 10,
                       db: Session = Depends(database)):
        start, end = parse_date(startDate), parse_date(endDate)
        if start > end:
            raise ValueError("startDate phải nhỏ hơn hoặc bằng endDate")
        query = select(DataSensor).join(DataSensor.sensor).where(
            Sensor.type == type, DataSensor.recorded_at >= start, DataSensor.recorded_at <= end
        ).order_by(DataSensor.recorded_at.desc(), DataSensor.id.desc())
        return envelope(paginate(db, query, page, size, data_dict), "Lọc dữ liệu cảm biến thành công")

    def history_page(db, device_id, status, start, end, page, size, inclusive=False, action=None, sort="desc"):
        if sort not in {"asc", "desc"}:
            raise ValueError("sort phải là asc hoặc desc")
        query = select(History)
        if device_id is not None:
            query = query.where(History.device_id == device_id)
        if status is not None:
            query = query.where(History.status == status)
        if action:
            if action not in {"ON", "OFF"}:
                raise ValueError("action phải là ON hoặc OFF")
            query = query.where(History.action == action)
        if start:
            query = query.where(History.timestamp >= start)
        if end:
            query = query.where(History.timestamp <= end if inclusive else History.timestamp < end)
        query = query.order_by(History.timestamp.asc(), History.id.asc()) if sort == "asc" else query.order_by(History.timestamp.desc(), History.id.desc())
        return paginate(db, query, page, size, history_dict)

    @app.get("/api/history", tags=["Lịch sử"], dependencies=[Depends(current_session)])
    def history(deviceId: int | None = None, status: str | None = None, startTime: str | None = None,
                endTime: str | None = None, page: int = 0, size: int = 10, action: str | None = None,
                sort: str = "desc", db: Session = Depends(database)):
        start, end = time_range(startTime, endTime)
        return envelope(history_page(db, deviceId, status, start, end, page, size, action=action, sort=sort), "Lấy lịch sử thành công")

    @app.get("/api/history/filter", tags=["Lịch sử"], dependencies=[Depends(current_session)])
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
        authorization = ws.headers.get("authorization", "").split()
        token = authorization[1] if len(authorization) == 2 and authorization[0].lower() == "bearer" else None
        if token is None:
            try:
                # Browsers cannot set Authorization on the WebSocket handshake.
                # Receive credentials in the first frame instead of a URL query.
                auth = await asyncio.wait_for(ws.receive_json(), WEBSOCKET_AUTH_TIMEOUT_SECONDS)
            except WebSocketDisconnect:
                return
            except (asyncio.TimeoutError, ValueError, TypeError, KeyError):
                await ws.close(code=4401)
                return
            token = auth.get("token") if isinstance(auth, dict) and auth.get("type") == "auth" else None
        if not await asyncio.to_thread(websocket_session_valid, token):
            await ws.close(code=4401)
            return
        await ws.send_json({"type": "authenticated"})
        queue = asyncio.Queue(maxsize=100)
        hub.subscribers.add(queue)

        async def send_events():
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), WEBSOCKET_SESSION_CHECK_SECONDS)
                except asyncio.TimeoutError:
                    event = None
                if not await asyncio.to_thread(websocket_session_valid, token):
                    await ws.close(code=4401)
                    group.cancel_scope.cancel()
                    return
                if event is not None and ws.query_params.get("topic") in (None, event["topic"]):
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
