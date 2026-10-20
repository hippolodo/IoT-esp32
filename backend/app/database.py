import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, create_engine, select, func, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


def now():
    # Match the old MySQL local datetime contract, regardless of host timezone.
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    pin_gpio: Mapped[int | None]
    status: Mapped[int | None]
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class Sensor(Base):
    __tablename__ = "sensors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(255))
    pin_gpio: Mapped[int | None]
    mqtt_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    module: Mapped[str | None] = mapped_column(String(255))


class DataSensor(Base):
    __tablename__ = "datasensors"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"))
    value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime, default=now)
    sensor: Mapped[Sensor] = relationship(lazy="joined")


class History(Base):
    __tablename__ = "histories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(255))
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, default=now)
    device: Mapped[Device | None] = relationship(lazy="joined")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)


def initialize_database(engine):
    Base.metadata.create_all(engine)
    # create_all does not add columns to existing tables. Preserve old history.
    if "user_id" not in {column["name"] for column in inspect(engine).get_columns("histories")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE histories ADD COLUMN user_id INTEGER NULL REFERENCES users(id)"))


def make_database(url):
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **options)
    return engine, sessionmaker(engine, expire_on_commit=False)


def seed_database(session_factory):
    # Never rewrite existing devices, sensor metadata, users or measurement history.
    with session_factory.begin() as db:
        if not db.scalar(select(func.count()).select_from(Device)):
            db.add_all([
                Device(name="Đèn phòng khách", pin_gpio=2, status=0, updated_at=now()),
                Device(name="Đèn phòng ngủ", pin_gpio=5, status=0, updated_at=now()),
            ])
        if not db.scalar(select(func.count()).select_from(Sensor)):
            db.add_all([
                Sensor(name="Cảm biến Nhiệt độ", type="TEMPERATURE", unit="°C", pin_gpio=4, mqtt_key="temperature", module="DHT11"),
                Sensor(name="Cảm biến Độ ẩm", type="HUMIDITY", unit="%", pin_gpio=4, mqtt_key="humidity", module="DHT11"),
                Sensor(name="Cảm biến Ánh sáng", type="LIGHT", unit="ADC", pin_gpio=33, mqtt_key="light", module="LDR"),
            ])
        if not db.scalar(select(func.count()).select_from(User)):
            db.add(User(username="admin", password_hash=hashlib.sha256(b"123456").hexdigest(),
                        full_name="Nguyễn Văn A", email="admin@gmail.com", created_at=now()))
