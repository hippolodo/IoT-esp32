import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from app.config import Settings
from app.database import DataSensor, Sensor, WindSpeed, initialize_database, make_database, seed_database
from app.main import create_app
from app.mqtt import MqttService


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'wind.sqlite'}", mqtt_enabled=False))
    with TestClient(app) as client:
        login = client.post('/api/auth/login', json={'username': 'admin', 'password': '123456'})
        client.headers['Authorization'] = f"Bearer {login.json()['data']['accessToken']}"
        yield client


def send(client, value):
    client.app.state.mqtt.handle_message('esp32/sensor/data', json.dumps({'windSpeed': value}))


def test_rename_legacy_alert_table_preserves_rows(tmp_path):
    engine, sessions = make_database(f"sqlite:///{tmp_path / 'legacy-wind.sqlite'}")
    try:
        initialize_database(engine)
        seed_database(sessions)
        with sessions.begin() as db:
            sensor_id = db.scalar(select(Sensor.id).where(Sensor.mqtt_key == 'windSpeed'))
            db.add(WindSpeed(sensor_id=sensor_id, speed=420, recorded_at=datetime(2026, 10, 21)))
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE "WindSpeed" RENAME TO wind_alerts'))
        initialize_database(engine)
        initialize_database(engine)
        tables = inspect(engine).get_table_names()
        assert 'WindSpeed' in tables and 'wind_alerts' not in tables
        with sessions() as db:
            rows = db.scalars(select(WindSpeed)).all()
            assert len(rows) == 1 and rows[0].speed == 420
    finally:
        engine.dispose()


def test_wind_seed_existing_installation_and_filter(client):
    with client.app.state.sessions.begin() as db:
        sensor = db.scalar(select(Sensor).where(Sensor.mqtt_key == 'windSpeed'))
        db.delete(sensor)
    # Simulate a database which already contains the original three sensors.
    seed_database(client.app.state.sessions)
    seed_database(client.app.state.sessions)
    sensors = client.get('/api/sensors').json()['data']
    assert len(sensors) == 4
    wind = next(s for s in sensors if s['type'] == 'WIND_SPEED')
    assert wind['unit'] == 'm/s' and wind['pinGpio'] is None
    send(client, 500)
    send(client, 0)
    page = client.get('/api/sensors/data?sensorType=WIND_SPEED&size=1').json()['data']
    assert page['totalElements'] == 2
    assert page['content'][0]['value'] == 0 and page['content'][0]['unit'] == 'm/s'
    assert client.get('/api/sensors/data?sensorType=WIND_SPEED&value=500').json()['data']['totalElements'] == 1
    latest = client.get('/api/sensors/latest').json()['data']
    assert next(row for row in latest if row['sensorType'] == 'WIND_SPEED')['value'] == 0
    devices = client.get('/api/devices').json()['data']
    assert len(devices) == 3
    assert next(d for d in devices if d['type'] == 'WIND_WARNING')['controllable'] is False


def test_warning_device_seed_state_and_control_protection(client):
    seed_database(client.app.state.sessions)
    devices = client.get('/api/devices').json()['data']
    warnings = [d for d in devices if d['type'] == 'WIND_WARNING']
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning['name'] == 'Đèn cảnh báo' and warning['pinGpio'] == 18
    send(client, 400)
    assert client.get(f"/api/devices/{warning['id']}").json()['data']['status'] == 1
    send(client, 300)
    assert client.get(f"/api/devices/{warning['id']}").json()['data']['status'] == 0
    # Even an accidental MQTT mapping must not make the automatic LED controllable.
    client.app.state.mqtt.settings.device_map[warning['id']] = 'led1'
    assert client.get(f"/api/devices/{warning['id']}").json()['data']['controllable'] is False
    response = client.post('/api/devices/control', json={'deviceId': warning['id'], 'status': 1})
    assert response.status_code == 400 and 'tự động' in response.json()['message']


def test_threshold_episodes_and_restart(client):
    for value in [300, 301, 400, 500]:
        send(client, value)
    with client.app.state.sessions() as db:
        assert len(db.scalars(select(WindSpeed)).all()) == 1
    old = client.app.state.mqtt
    restarted = MqttService(old.settings, old.sessions, old.hub)
    restarted.handle_message('esp32/sensor/data', '{"windSpeed":450}')
    for value in [300, 301, 0, 500]:
        send(client, value)
    with client.app.state.sessions() as db:
        alerts = db.scalars(select(WindSpeed).order_by(WindSpeed.id)).all()
        assert [row.speed for row in alerts] == [301, 301, 500]
        assert len(db.scalars(select(DataSensor)).all()) == 9


def test_new_alert_event_only_after_committed_episode(client, monkeypatch):
    events = []

    def receive(topic, data, **kwargs):
        if topic == '/topic/wind-alerts':
            # A different DB session must already see the committed alert.
            with client.app.state.sessions() as db:
                alert = db.get(WindSpeed, data['id'])
                assert alert is not None and alert.speed == data['speed']
            events.append(data)

    monkeypatch.setattr(client.app.state.hub, 'emit', receive)
    for speed in [200, 350, 400, 300, 450]:
        send(client, speed)
    assert [event['speed'] for event in events] == [350, 450]
    assert all(len(event['recordedAt']) == 19 for event in events)


@pytest.mark.parametrize('value', [-1, 501, True, '400', None, float('nan'), float('inf')])
def test_invalid_speed_not_saved_or_counted(client, value):
    send(client, value)
    with client.app.state.sessions() as db:
        assert not db.scalars(select(DataSensor)).all()
        assert not db.scalars(select(WindSpeed)).all()


@pytest.mark.parametrize('month,length', [('2026-02', 28), ('2024-02', 29), ('2026-04', 30), ('2026-10', 31)])
def test_calendar_days_including_zero_counts(client, month, length):
    result = client.get('/api/alerts/wind/summary', params={'month': month}).json()['data']
    assert len(result['days']) == length and result['total'] == 0
    assert result['days'][0] == {'date': month + '-01', 'count': 0}
    assert result['days'][-1]['date'] == f'{month}-{length}'


def test_month_day_boundaries_and_pagination(client):
    with client.app.state.sessions.begin() as db:
        sensor_id = db.scalar(select(Sensor.id).where(Sensor.mqtt_key == 'windSpeed'))
        db.add_all([WindSpeed(sensor_id=sensor_id, speed=350 + i, recorded_at=date) for i, date in enumerate([
            datetime(2026, 9, 30, 23, 59, 59), datetime(2026, 10, 1),
            datetime(2026, 10, 1, 23, 59, 59), datetime(2026, 10, 31, 23, 59, 59), datetime(2026, 11, 1),
        ])])
    summary = client.get('/api/alerts/wind/summary?month=2026-10').json()['data']
    assert summary['total'] == 3
    assert summary['days'][0]['count'] == 2 and summary['days'][-1]['count'] == 1
    assert summary['days'][1]['count'] == 0
    page = client.get('/api/alerts/wind?date=2026-10-01&size=1&page=1').json()['data']
    assert page['totalElements'] == 2 and page['totalPages'] == 2
    assert page['content'][0]['recordedAt'] == '2026-10-01 00:00:00'


@pytest.mark.parametrize('path', [
    '/api/alerts/wind/summary?month=2026-13', '/api/alerts/wind/summary?month=2026-2',
    '/api/alerts/wind/summary?month=0000-01', '/api/alerts/wind?date=2026-02-30',
    '/api/alerts/wind?date=2026-10-01 12:00', '/api/alerts/wind?date=2026-10-01&size=0',
    '/api/alerts/wind?date=2026-10-01&page=-1',
])
def test_invalid_filters(client, path):
    assert client.get(path).status_code == 400


@pytest.mark.parametrize('path', ['/api/alerts/wind/summary?month=2026-10', '/api/alerts/wind?date=2026-10-01'])
def test_statistics_require_auth(client, path):
    client.headers.pop('Authorization')
    assert client.get(path).status_code == 401


def test_warning_device_history_filters_and_pagination(client):
    with client.app.state.sessions.begin() as db:
        sensor_id = db.scalar(select(Sensor.id).where(Sensor.mqtt_key == 'windSpeed'))
        db.add_all([WindSpeed(sensor_id=sensor_id, speed=350 + day, recorded_at=datetime(2026, 10, day))
                    for day in [20, 21, 22]])
    path = '/api/history?deviceType=WIND_WARNING'
    page = client.get(path + '&size=1&page=1&sort=asc').json()['data']
    assert page['totalElements'] == 3 and page['totalPages'] == 3
    row = page['content'][0]
    assert row['deviceName'] == 'Đèn cảnh báo' and row['userId'] is None
    assert row['eventType'] == 'WIND_WARNING' and row['status'] == 'RECORDED'
    assert row['action'] == 'ALERT' and row['speed'] == 371
    assert client.get(path + '&status=RECORDED&action=ALERT').json()['data']['totalElements'] == 3
    assert client.get(path + '&action=OFF').json()['data']['totalElements'] == 0
    assert client.get(path + '&status=FAILED').json()['data']['totalElements'] == 0
    dates = '&startTime=2026-10-21&endTime=2026-10-21'
    assert client.get(path + dates).json()['data']['totalElements'] == 1
    assert client.get(path + '&sort=bad').status_code == 400
    assert client.get(path + '&deviceId=1').status_code == 400
    assert client.get('/api/history?deviceType=bad').status_code == 400
    assert client.get('/api/history').json()['data']['totalElements'] == 0
    client.headers.pop('Authorization')
    assert client.get(path).status_code == 401
