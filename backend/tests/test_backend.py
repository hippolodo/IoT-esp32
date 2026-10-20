import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts import time_range
from app.database import AuthSession, DataSensor, Device, History, Sensor, User, initialize_database, make_database, now, seed_database
from app.main import create_app


def test_swagger_declares_bearer_auth_for_protected_routes(client):
    schema = client.get('/openapi.json').json()
    assert schema['components']['securitySchemes']['HTTPBearer']['scheme'] == 'bearer'
    for path, method in [('/api/devices/control', 'post'), ('/api/user/profile', 'get'), ('/api/auth/logout', 'post')]:
        assert schema['paths'][path][method]['security'] == [{'HTTPBearer': []}]
    assert not schema['paths']['/api/auth/login']['post'].get('security')


def test_control_requires_verified_session(client, connected):
    original = client.headers.pop('Authorization')
    body = {'deviceId': 1, 'status': 1, 'userId': 1}
    assert client.post('/api/devices/control', json=body).status_code == 401
    client.headers['Authorization'] = 'Bearer forged-token'
    assert client.post('/api/devices/control', json=body).status_code == 401
    connected.client.publish.assert_not_called()
    client.headers['Authorization'] = original


def test_control_uses_logged_in_user_and_logout_revokes_session(client, connected):
    with client.app.state.sessions.begin() as db:
        user = User(username='operator', password_hash=hashlib.sha256(b'secret').hexdigest())
        db.add(user)
        db.flush()
        user_id = user.id
    result = client.post('/api/auth/login', json={'username': 'operator', 'password': 'secret'}).json()['data']
    token = result['accessToken']
    client.headers['Authorization'] = f'Bearer {token}'
    assert client.get('/api/user/profile').json()['data']['id'] == user_id
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 1, 'userId': 1}).status_code == 200
    connected.handle_message('esp32/led1/status', 'ON')
    row = client.get('/api/history').json()['data']['content'][0]
    assert row['userId'] == user_id and row['status'] == 'SUCCESS'
    with client.app.state.sessions() as db:
        assert db.get(AuthSession, token) is None
    assert client.post('/api/auth/logout').status_code == 200
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 0}).status_code == 401


def test_expired_session_cannot_control(client, connected):
    token = client.headers['Authorization'].split()[1]
    with client.app.state.sessions.begin() as db:
        db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()).expires_at = now() - timedelta(seconds=1)
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 1}).status_code == 401
    connected.client.publish.assert_not_called()


def test_existing_history_migration_preserves_rows(tmp_path):
    from sqlalchemy import text
    engine, sessions = make_database(f"sqlite:///{tmp_path / 'legacy.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE histories (id INTEGER PRIMARY KEY, device_id INTEGER, action VARCHAR(255), status VARCHAR(255), timestamp DATETIME)'))
        connection.execute(text("INSERT INTO histories (id, action, status) VALUES (1, 'ON', 'SUCCESS')"))
    initialize_database(engine)
    initialize_database(engine)
    with sessions() as db:
        row = db.get(History, 1)
        assert row.action == 'ON' and row.user_id is None
    engine.dispose()


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}", mqtt_enabled=False)
    app = create_app(settings)
    with TestClient(app) as client:
        token = client.post('/api/auth/login', json={'username': 'admin', 'password': '123456'}).json()['data']['accessToken']
        client.headers['Authorization'] = f'Bearer {token}'
        yield client


@pytest.fixture
def connected(client):
    service = client.app.state.mqtt
    service.settings.mqtt_enabled = True
    service.client = Mock()
    service.client.is_connected.return_value = True
    service.client.publish.return_value = SimpleNamespace(rc=0)
    return service


def test_health_login_and_profile(client):
    assert client.get('/api/auth/health').json() == {
        'success': True, 'message': 'Backend đang chạy', 'data': 'OK', 'code': 200}
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': '123456'})
    assert response.status_code == 200
    assert response.json()['data']['userId'] == 1
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': 'bad'}).status_code == 401
    assert client.post('/api/auth/login', json={}).status_code == 400
    profile = client.get('/api/user/profile').json()['data']
    assert profile['username'] == 'admin'
    assert 'passwordHash' not in profile


def test_devices_and_validation(client):
    devices = client.get('/api/devices').json()['data']
    assert [d['pinGpio'] for d in devices] == [2, 5]
    assert client.get('/api/devices/1').json()['data'] == devices[0]
    assert client.get('/api/devices/999').status_code == 404
    assert client.get('/missing').json()['code'] == 404
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 2}).status_code == 400
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': True}).status_code == 400
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 1}).status_code == 503
    assert client.get('/api/history').json()['data']['totalElements'] == 0


def test_sensor_ingestion_and_pagination(client):
    mqtt = client.app.state.mqtt
    mqtt.handle_message('esp32/sensor/data', '{"temperature":28.5,"humidity":65,"light":1500}')
    mqtt.handle_message('esp32/sensor/data', '{"error":"DHT error","light":1600}')
    sensors = client.get('/api/sensors').json()['data']
    assert [s['mqttKey'] for s in sensors] == ['temperature', 'humidity', 'light']
    latest = client.get('/api/sensors/latest').json()['data']
    assert len(latest) == 3
    assert next(row for row in latest if row['sensorType'] == 'LIGHT')['value'] == 1600
    page = client.get('/api/sensors/data', params={'size': 2}).json()['data']
    assert page['totalElements'] == 4 and page['totalPages'] == 2
    assert len(page['content']) == 2 and not page['last']
    assert client.get('/api/sensors/data', params={'sensorId': 3}).json()['data']['totalElements'] == 2
    assert client.get('/api/sensors/data?page=-1').status_code == 400
    assert client.get('/api/sensors/data?size=0').status_code == 400


def test_date_filters(client):
    with client.app.state.sessions.begin() as db:
        db.add_all([DataSensor(sensor_id=1, value=i, recorded_at=datetime(2026, 10, day, 23, 59, 59))
                    for i, day in enumerate([16, 17, 18])])
    response = client.get('/api/sensors/data', params={'startTime': '2026-10-17', 'endTime': '2026-10-17'})
    assert response.json()['data']['totalElements'] == 1
    response = client.get('/api/sensors/filter', params={
        'type': 'TEMPERATURE', 'startDate': '2026-10-17 00:00:00', 'endDate': '2026-10-17 23:59:59'})
    assert response.json()['data']['totalElements'] == 1
    for params in ({'startTime': '2026-10-17'}, {'startTime': 'bad', 'endTime': 'bad'},
                   {'startTime': '2026-10-18', 'endTime': '2026-10-17'}):
        assert client.get('/api/sensors/data', params=params).status_code == 400
    assert client.get('/api/sensors/filter').status_code == 400


def test_command_ack_updates_one_history(client, connected):
    response = client.post('/api/devices/control', json={'deviceId': 1, 'status': 1})
    assert response.json()['data'] == 'OK'
    connected.client.publish.assert_called_once_with('esp32/led1/control', 'ON', qos=1, retain=False)
    assert client.get('/api/devices/1').json()['data']['status'] == 0
    assert client.get('/api/history').json()['data']['content'][0]['status'] == 'PENDING'
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 0}).status_code == 409
    connected.handle_message('esp32/led1/status', 'ON')
    connected.handle_message('esp32/led1/status', 'ON')
    assert client.get('/api/devices/1').json()['data']['status'] == 1
    history = client.get('/api/history').json()['data']
    assert history['totalElements'] == 1
    assert history['content'][0]['status'] == 'SUCCESS'
    assert history['content'][0]['userId'] == 1
    assert client.get('/api/history/filter?deviceId=1&status=SUCCESS').json()['data']['totalElements'] == 1
    assert client.get('/api/history/filter').status_code == 400


def test_retained_and_failed_status(client, connected):
    client.post('/api/devices/control', json={'deviceId': 2, 'status': 1})
    connected.handle_message('esp32/led2/status', 'ON', retained=True)
    assert client.get('/api/history').json()['data']['content'][0]['status'] == 'PENDING'
    connected.handle_message('esp32/led2/status', 'FAIL')
    row = client.get('/api/history').json()['data']['content'][0]
    assert row['status'] == 'FAILED'
    # FAIL is never interpreted as an OFF snapshot.
    assert client.get('/api/devices/2').json()['data']['status'] == 1


def test_publish_failure_timeout_and_unmapped(client, connected):
    connected.client.publish.return_value.rc = 4
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 1}).status_code == 503
    assert client.get('/api/history').json()['data']['content'][0]['status'] == 'FAILED'
    with client.app.state.sessions.begin() as db:
        db.add(Device(id=3, name='Existing third lamp', pin_gpio=21, status=0))
        db.add(History(device_id=2, action='ON', status='PENDING', timestamp=now() - timedelta(minutes=1)))
    connected.expire_pending()
    assert client.get('/api/history?status=PENDING').json()['data']['totalElements'] == 0
    assert client.post('/api/devices/control', json={'deviceId': 3, 'status': 1}).status_code == 400
    assert client.post('/api/devices/control', json={'deviceId': 999, 'status': 1}).status_code == 404


def test_websocket_sensor_and_device_events(client):
    with client.websocket_connect('/ws') as ws:
        client.app.state.mqtt.handle_message('esp32/sensor/data', '{"light":123}')
        assert ws.receive_json() == {'topic': '/topic/sensors', 'data': {'light': 123}}
        client.app.state.mqtt.handle_message('esp32/led1/status', 'ON')
        event = ws.receive_json()
        assert event['topic'] == '/topic/device-status'
        assert event['data']['status'] == 1


def test_websocket_topic_filter(client):
    with client.websocket_connect('/ws?topic=/topic/device-status') as ws:
        client.app.state.mqtt.handle_message('esp32/sensor/data', '{"light":123}')
        client.app.state.mqtt.handle_message('esp32/led2/status', 'OFF')
        assert ws.receive_json()['topic'] == '/topic/device-status'


def test_reconnect_resubscribes_and_invalid_sensor_values(client):
    service = client.app.state.mqtt
    fake = Mock()
    service._on_connect(fake, None, None, SimpleNamespace(is_failure=False), None)
    topics = dict(fake.subscribe.call_args.args[0])
    assert topics['esp32/sensor/data'] == 1 and topics['esp32/led2/status'] == 1
    service.handle_message('esp32/sensor/data', '{"light":true,"temperature":NaN,"humidity":"bad"}')
    assert client.get('/api/sensors/data').json()['data']['totalElements'] == 0
    with pytest.raises(ValueError):
        service.handle_message('esp32/sensor/data', '[]')


def test_seed_preserves_existing_data_and_sha256_login(client):
    with client.app.state.sessions.begin() as db:
        db.get(Device, 1).pin_gpio = 18
        db.get(Sensor, 3).unit = 'legacy'
    seed_database(client.app.state.sessions)
    assert client.get('/api/devices/1').json()['data']['pinGpio'] == 18
    assert client.get('/api/sensors').json()['data'][2]['unit'] == 'legacy'
    assert client.post('/api/auth/login', json={'username': 'admin', 'password': '123456'}).status_code == 200


@pytest.mark.parametrize('value,expected_seconds', [
    ('2026-10-17', 86400), ('2026-10-17 15', 3600),
    ('2026-10-17 15:30', 60), ('2026-10-17 15:30:45', 1),
])
def test_time_range_precision(value, expected_seconds):
    start, end = time_range(value, value)
    assert (end - start).total_seconds() == expected_seconds


def test_publish_exception_marks_history_failed(client, connected):
    connected.client.publish.side_effect = OSError('disconnected')
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 1}).status_code == 503
    assert client.get('/api/history').json()['data']['content'][0]['status'] == 'FAILED'


def test_websocket_rejects_foreign_origin(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws', headers={'origin': 'https://example.com'}):
            pytest.fail('Foreign origin should not be accepted')


def test_connection_status_and_capabilities(client, connected):
    from time import monotonic
    assert client.get('/api/system/status').json()['data']['mqttConnected'] is True
    connected.handle_message('esp32/sensor/data', '{"light":1200}')
    assert client.get('/api/system/status').json()['data']['esp32Online'] is True
    connected.last_seen = monotonic() - 21
    assert client.get('/api/system/status').json()['data']['esp32Online'] is False
    connected._on_disconnect(None, None, None, None, None)
    assert connected.connection_status()['esp32Online'] is None
    device = client.get('/api/devices/1').json()['data']
    assert device['controllable'] is True and device['controlPin'] == 2 and device['pending'] is False
    client.post('/api/devices/control', json={'deviceId': 1, 'status': 1})
    assert client.get('/api/devices/1').json()['data']['pending'] is True
    connected.handle_message('esp32/led1/status', 'ON')
    assert client.get('/api/devices/1').json()['data']['pending'] is False


def test_server_side_sensor_filters(client):
    service = client.app.state.mqtt
    service.handle_message('esp32/sensor/data', '{"temperature":28.5,"humidity":60,"light":1500}')
    service.handle_message('esp32/sensor/data', '{"temperature":29.5,"light":1600}')
    page = client.get('/api/sensors/data', params={'sensorType': 'temperature', 'value': '28.5'}).json()['data']
    assert page['totalElements'] == 1 and page['content'][0]['value'] == 28.5
    assert client.get('/api/sensors/data?sensorType=LIGHT&size=1&page=1').json()['data']['totalElements'] == 2


def test_history_action_and_sort_filters(client):
    with client.app.state.sessions.begin() as db:
        for i, action in enumerate(['ON', 'OFF', 'ON']):
            db.add(History(device_id=1, action=action, status='SUCCESS', timestamp=datetime(2026, 10, 18, 10, i)))
    page = client.get('/api/history?action=ON&sort=asc&size=1').json()['data']
    assert page['totalElements'] == 2 and page['content'][0]['timestamp'].endswith('10:00:00')
    assert client.get('/api/history?action=ON&sort=desc').json()['data']['content'][0]['timestamp'].endswith('10:02:00')
    assert client.get('/api/history?action=bad').status_code == 400
    assert client.get('/api/history?sort=bad').status_code == 400
