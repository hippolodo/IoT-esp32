"""Application factory, lifecycle, middleware and router registration."""
import asyncio
import logging
import threading
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import Settings
from .database import make_database
from .contracts import register_exception_handlers
from .routers import alerts, auth, devices, history, realtime, sensors, system
from .services.mqtt import EventHub, MqttService

log = logging.getLogger(__name__)
COMMAND_CHECK_INTERVAL_SECONDS = 1


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
                log.exception('Failed to expire pending commands')

    @asynccontextmanager
    async def lifespan(app):
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
            {"name": "Cảnh báo gió", "description": "Đếm đợt vượt 300 m/s theo ngày và tháng, xem chi tiết từng ngày."},
            {"name": "Hệ thống", "description": "Kiểm tra backend và trạng thái kết nối MQTT, ESP32."},
        ],
    )
    app.state.sessions, app.state.mqtt, app.state.hub = (sessions, mqtt, hub)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.registration_lock = registration_lock
    register_exception_handlers(app)
    for router in (
        system.router, auth.router, devices.router,
        alerts.router, sensors.router, history.router, realtime.router,
    ):
        app.include_router(router)
    return app


app = create_app()
