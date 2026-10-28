"""Explicit fixtures for temporary SQLite tests; never used by app startup."""
import hashlib
from sqlalchemy import func, select
from app.contracts import now
from app.models import Base, Device, Sensor, User


def prepare_test_database(app):
    sessions = app.state.sessions
    engine = sessions.kw['bind']
    if engine.dialect.name != 'sqlite':
        raise ValueError('Test fixtures may only prepare temporary SQLite databases')
    Base.metadata.create_all(engine)
    with sessions.begin() as db:
        db.add_all([
            Device(id=1, name='Đèn 1 · Nhiệt độ', pin_gpio=2, status=0, updated_at=now()),
            Device(id=2, name='Đèn 2 · Độ ẩm', pin_gpio=5, status=0, updated_at=now()),
            Device(id=3, name='Đèn 3 · Ánh sáng', device_type='LIGHT', pin_gpio=18, status=0, updated_at=now()),
            Sensor(id=1, name='Cảm biến Nhiệt độ', type='TEMPERATURE', unit='°C', pin_gpio=4, mqtt_key='temperature', module='DHT11'),
            Sensor(id=2, name='Cảm biến Độ ẩm', type='HUMIDITY', unit='%', pin_gpio=4, mqtt_key='humidity', module='DHT11'),
            Sensor(id=3, name='Cảm biến Ánh sáng', type='LIGHT', unit='ADC', pin_gpio=33, mqtt_key='light', module='LDR'),
        ])
        if not db.scalar(select(func.count()).select_from(User)):
            db.add(User(id=1, username='admin', password_hash=hashlib.sha256(b'123456').hexdigest(),
                        full_name='Nguyễn Văn A', email='admin@gmail.com', created_at=now()))
