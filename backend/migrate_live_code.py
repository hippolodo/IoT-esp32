"""Update only the three LED catalog rows. Existing measurements are preserved."""
from app.config import Settings
from app.database import make_database
from app.models import Device
from app.contracts import now


def migrate():
    settings = Settings()
    engine, sessions = make_database(settings.database_url)
    names = {'led1': 'Đèn 1 · Nhiệt độ', 'led2': 'Đèn 2 · Độ ẩm', 'led3': 'Đèn 3 · Ánh sáng'}
    pins = {'led1': 2, 'led2': 5, 'led3': 18}
    try:
        with sessions.begin() as db:
            for device_id, led in settings.device_map.items():
                device = db.get(Device, device_id)
                if device is None:
                    device = Device(id=device_id, status=0, updated_at=now())
                    db.add(device)
                device.name = names[led]
                device.device_type = 'LIGHT'
                device.pin_gpio = pins[led]
        print('Updated three LED catalog entries; historical data preserved.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    migrate()
