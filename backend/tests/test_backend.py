import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts import now, time_range
from app.database import make_database
from db_setup import prepare_test_database
from app.models import AuthSession, DataSensor, Device, History, Sensor, User
from app.main import create_app
from app.passwords import verify_password


def registration_body(**overrides):
    return {
        'username': 'new_user', 'fullName': 'Nguyễn Văn Hiệp',
        'email': 'hiep@example.com', 'password': 'Test-password-123',
        'confirmPassword': 'Test-password-123', **overrides,
    }


def test_startup_does_not_create_tables(tmp_path):
    from sqlalchemy import inspect
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'empty.sqlite'}", mqtt_enabled=False))
    with TestClient(app) as client:
        assert client.get('/api/auth/health').status_code == 200
        assert inspect(app.state.sessions.kw['bind']).get_table_names() == []


def test_startup_does_not_add_or_rewrite_catalog_data(tmp_path):
    from sqlalchemy import func, select
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'existing.sqlite'}", mqtt_enabled=False))
    prepare_test_database(app)
    with app.state.sessions.begin() as db:
        db.delete(db.get(Device, 3))
        db.delete(db.get(Sensor, 4))
        db.get(User, 1).full_name = 'Existing user'
    with TestClient(app) as client:
        assert client.get('/api/auth/health').status_code == 200
        with app.state.sessions() as db:
            assert db.scalar(select(func.count()).select_from(Device)) == 2
            assert db.scalar(select(func.count()).select_from(Sensor)) == 3
            assert db.get(User, 1).full_name == 'Existing user'


def test_registration_login_profile_and_control(client, connected):
    client.headers.pop('Authorization')
    body = registration_body(username='  NEW_User  ', email='  Hiep@Example.COM  ')
    response = client.post('/api/auth/register', json=body)
    assert response.status_code == 201
    result = response.json()
    assert result['code'] == 201 and result['success'] is True
    user = result['data']
    assert user['username'] == 'new_user'
    assert user['email'] == 'hiep@example.com' and user['fullName'] == 'Nguyễn Văn Hiệp'
    assert not any('password' in key.lower() or 'token' in key.lower() for key in user)
    with client.app.state.sessions() as db:
        saved = db.get(User, user['userId'])
        assert saved.password_hash.startswith('pbkdf2_sha256$')
        assert body['password'] not in saved.password_hash
        assert verify_password(body['password'], saved.password_hash)
    assert client.post('/api/auth/login', json={'username': 'new_user', 'password': 'wrong-password'}).status_code == 401
    login = client.post('/api/auth/login', json={'username': ' NEW_USER ', 'password': body['password']})
    assert login.status_code == 200
    client.headers['Authorization'] = f"Bearer {login.json()['data']['accessToken']}"
    assert client.get('/api/user/profile').json()['data']['id'] == user['userId']
    assert client.post('/api/devices/control', json={'deviceId': 1, 'status': 1}).status_code == 200
    connected.handle_message('esp32/led1/status', 'ON')
    history = client.get('/api/history').json()['data']['content'][0]
    assert history['userId'] == user['userId'] and history['status'] == 'SUCCESS'


@pytest.mark.parametrize('overrides', [
    {'username': 'ab'}, {'username': 'a' * 51}, {'username': 'bad user'},
    {'username': 'user<script>'}, {'username': None},
    {'fullName': '   '}, {'fullName': 'a' * 256},
    {'email': 'not-an-email'}, {'email': 'name @example.com'}, {'email': 'a' * 256 + '@test.com'},
    {'password': 'short', 'confirmPassword': 'short'},
    {'password': 'a' * 129, 'confirmPassword': 'a' * 129},
    {'password': '        ', 'confirmPassword': '        '},
    {'confirmPassword': 'different-password'},
])
def test_registration_rejects_invalid_data(client, overrides):
    assert client.post('/api/auth/register', json=registration_body(**overrides)).status_code == 400
    with client.app.state.sessions() as db:
        assert len(db.query(User).all()) == 1


def test_registration_requires_fields_and_rejects_duplicates(client):
    assert client.post('/api/auth/register', json={}).status_code == 400
    assert client.post('/api/auth/register', json=registration_body(username=' ADMIN ')).status_code == 409
    assert client.post('/api/auth/register', json=registration_body(email='ADMIN@GMAIL.COM')).status_code == 409
    assert client.post('/api/auth/register', json=registration_body()).status_code == 201
    assert client.post('/api/auth/register', json=registration_body(email='other@example.com')).status_code == 409
    assert client.post('/api/auth/register', json=registration_body(username='other', email='HIEP@EXAMPLE.COM')).status_code == 409
    with client.app.state.sessions() as db:
        assert len(db.query(User).all()) == 2


def test_user_uniqueness_is_enforced_by_database(client):
    from sqlalchemy.exc import IntegrityError
    for username, email in [('admin', 'different@example.com'), ('different', 'admin@gmail.com')]:
        with pytest.raises(IntegrityError):
            with client.app.state.sessions.begin() as db:
                db.add(User(username=username, email=email, password_hash='unused'))


def test_password_salts_and_legacy_compatibility():
    from app.passwords import hash_password
    one, two = hash_password('Test-password-123'), hash_password('Test-password-123')
    assert one != two
    assert verify_password('Test-password-123', one)
    assert not verify_password('wrong-password', one)
    assert verify_password('legacy', hashlib.sha256(b'legacy').hexdigest())
    assert not verify_password('wrong', hashlib.sha256(b'legacy').hexdigest())
    assert not verify_password('test', 'pbkdf2_sha256$bad$salt$hash')
    assert not verify_password('test', 'pbkdf2_sha256$999999999$salt$' + '0' * 64)


def test_registration_preserves_legacy_duplicates(tmp_path):
    from sqlalchemy import text
    url = f"sqlite:///{tmp_path / 'duplicate-users.sqlite3'}"
    engine, sessions = make_database(url)
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL, full_name VARCHAR(255), email VARCHAR(255), created_at DATETIME)'))
        connection.execute(text("INSERT INTO users (id, username, password_hash, email) VALUES (1, 'legacy', 'unchanged', 'old@example.com'), (2, 'legacy', 'unchanged', 'old@example.com')"))
    engine.dispose()
    app = create_app(Settings(database_url=url, mqtt_enabled=False))
    prepare_test_database(app)
    with TestClient(app) as client:
        with app.state.sessions() as db:
            assert len(db.query(User).all()) == 2
        assert client.post('/api/auth/register', json=registration_body(username='LEGACY')).status_code == 409
        assert client.post('/api/auth/register', json=registration_body(email='OLD@EXAMPLE.COM')).status_code == 409
        assert client.post('/api/auth/register', json=registration_body()).status_code == 201
        assert client.post('/api/auth/register', json=registration_body(email='different@example.com')).status_code == 409


def test_swagger_declares_bearer_auth_for_protected_routes(client):
    schema = client.get('/openapi.json').json()
    assert schema['components']['securitySchemes']['HTTPBearer']['scheme'] == 'bearer'
    for path, method in [('/api/devices/control', 'post'), ('/api/user/profile', 'get'), ('/api/auth/logout', 'post')]:
        assert schema['paths'][path][method]['security'] == [{'HTTPBearer': []}]
    assert not schema['paths']['/api/auth/login']['post'].get('security')
    assert not schema['paths']['/api/auth/register']['post'].get('security')
    public = {'/api/auth/health', '/api/auth/login', '/api/auth/register'}
    for path, operations in schema['paths'].items():
        for method, operation in operations.items():
            if method not in {'get', 'post'}:
                continue
            assert bool(operation.get('security')) == (path not in public)


PROTECTED_GETS = [
    '/api/system/status', '/api/user/profile', '/api/devices', '/api/devices/1',
    '/api/sensors', '/api/sensors/latest', '/api/sensors/data',
    '/api/sensors/filter?type=LIGHT&startDate=2026-10-21&endDate=2026-10-21',
    '/api/history', '/api/history/filter?deviceId=1&status=SUCCESS',
]


@pytest.mark.parametrize('path', PROTECTED_GETS)
def test_read_apis_require_valid_session(client, path):
    original = client.headers.pop('Authorization')
    response = client.get(path)
    assert response.status_code == 401 and response.json()['success'] is False
    client.headers['Authorization'] = 'Bearer forged-token'
    assert client.get(path).status_code == 401
    client.headers['Authorization'] = original
    assert client.get(path).status_code == 200


@pytest.mark.parametrize('revoke', ['expired', 'logout'])
def test_read_apis_reject_expired_or_revoked_session(client, revoke):
    if revoke == 'logout':
        assert client.post('/api/auth/logout').status_code == 200
    else:
        token = client.headers['Authorization'].split()[1]
        with client.app.state.sessions.begin() as db:
            db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()).expires_at = now() - timedelta(seconds=1)
    for path in PROTECTED_GETS:
        assert client.get(path).status_code == 401
    assert client.get('/api/auth/health').status_code == 200


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


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}", mqtt_enabled=False)
    app = create_app(settings)
    prepare_test_database(app)
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
    assert [d['pinGpio'] for d in devices] == [2, 5, 18]
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
    assert [s['mqttKey'] for s in sensors] == ['temperature', 'humidity', 'light', 'windSpeed']
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
        db.add(Device(id=99, name='Existing unmapped lamp', pin_gpio=21, status=0))
        db.add(History(device_id=2, action='ON', status='PENDING', timestamp=now() - timedelta(minutes=1)))
    connected.expire_pending()
    assert client.get('/api/history?status=PENDING').json()['data']['totalElements'] == 0
    assert client.post('/api/devices/control', json={'deviceId': 99, 'status': 1}).status_code == 400
    assert client.post('/api/devices/control', json={'deviceId': 999, 'status': 1}).status_code == 404


def test_websocket_sensor_and_device_events(client):
    with client.websocket_connect('/ws') as ws:
        assert ws.receive_json() == {'type': 'authenticated'}
        client.app.state.mqtt.handle_message('esp32/sensor/data', '{"light":123}')
        event = ws.receive_json()
        assert event['topic'] == '/topic/sensors' and event['data'] == {'light': 123}
        assert event['recordedAt'] == client.get('/api/sensors/latest').json()['data'][0]['recordedAt']
        client.app.state.mqtt.handle_message('esp32/led1/status', 'ON')
        event = ws.receive_json()
        assert event['topic'] == '/topic/device-status'
        assert event['data']['status'] == 1


def test_websocket_topic_filter(client):
    with client.websocket_connect('/ws?topic=/topic/device-status') as ws:
        assert ws.receive_json() == {'type': 'authenticated'}
        client.app.state.mqtt.handle_message('esp32/sensor/data', '{"light":123}')
        client.app.state.mqtt.handle_message('esp32/led2/status', 'OFF')
        assert ws.receive_json()['topic'] == '/topic/device-status'


def test_browser_websocket_authenticates_first_frame(client):
    token = client.headers['Authorization'].split()[1]
    with client.websocket_connect('/ws?topic=/topic/sensors', headers={'Authorization': ''}) as ws:
        ws.send_json({'type': 'auth', 'token': token})
        assert ws.receive_json() == {'type': 'authenticated'}
        client.app.state.mqtt.handle_message('esp32/sensor/data', '{"light":123}')
        event = ws.receive_json()
        assert event['topic'] == '/topic/sensors' and event['data'] == {'light': 123}
        assert event['recordedAt'] == client.get('/api/sensors/latest').json()['data'][0]['recordedAt']


@pytest.mark.parametrize('auth', [{}, {'type': 'auth', 'token': 'forged'},
                                   {'type': 'auth', 'token': None}, ['not-an-object']])
def test_websocket_rejects_invalid_auth_frame(client, auth):
    from starlette.websockets import WebSocketDisconnect
    with client.websocket_connect('/ws', headers={'Authorization': ''}) as ws:
        ws.send_json(auth)
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4401
    assert not client.app.state.hub.subscribers


def test_websocket_requires_auth_before_subscribing(client, monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    monkeypatch.setattr('app.routers.realtime.WEBSOCKET_AUTH_TIMEOUT_SECONDS', 0.02)
    with client.websocket_connect('/ws', headers={'Authorization': ''}) as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4401
    assert not client.app.state.hub.subscribers


@pytest.mark.parametrize('revoke', ['expired', 'logout'])
def test_open_websocket_closes_when_session_invalid_without_events(client, monkeypatch, revoke):
    from starlette.websockets import WebSocketDisconnect
    monkeypatch.setattr('app.routers.realtime.WEBSOCKET_SESSION_CHECK_SECONDS', 0.02)
    with client.websocket_connect('/ws') as ws:
        assert ws.receive_json() == {'type': 'authenticated'}
        if revoke == 'logout':
            assert client.post('/api/auth/logout').status_code == 200
        else:
            token = client.headers['Authorization'].split()[1]
            with client.app.state.sessions.begin() as db:
                db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()).expires_at = now() - timedelta(seconds=1)
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4401
    assert not client.app.state.hub.subscribers


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


def test_chart_history_empty_and_authentication(client):
    assert client.get('/api/sensors/chart').json()['data'] == []
    for limit in [0, 31, -1]:
        assert client.get('/api/sensors/chart', params={'limit': limit}).status_code == 400
    client.headers.pop('Authorization')
    assert client.get('/api/sensors/chart').status_code == 401


def test_app_instances_keep_database_auth_and_mqtt_separate(tmp_path):
    first_app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'first.sqlite'}", mqtt_enabled=False,
                                    device_map={1: 'led1'}))
    second_app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'second.sqlite'}", mqtt_enabled=False,
                                     device_map={2: 'led2'}))
    prepare_test_database(first_app)
    prepare_test_database(second_app)
    with TestClient(first_app) as first, TestClient(second_app) as second:
        credentials = {'username': 'admin', 'password': '123456'}
        first_token = first.post('/api/auth/login', json=credentials).json()['data']['accessToken']
        second_token = second.post('/api/auth/login', json=credentials).json()['data']['accessToken']
        first.headers['Authorization'] = f'Bearer {first_token}'
        second.headers['Authorization'] = f'Bearer {first_token}'
        assert second.get('/api/user/profile').status_code == 401
        second.headers['Authorization'] = f'Bearer {second_token}'
        assert second.get('/api/user/profile').status_code == 200
        first_app.state.mqtt.handle_message('esp32/sensor/data', '{"light":123}')
        second_app.state.mqtt.handle_message('esp32/sensor/data', '{"light":456}')
        assert first.get('/api/sensors/latest').json()['data'][0]['value'] == 123
        assert second.get('/api/sensors/latest').json()['data'][0]['value'] == 456
        assert first.get('/api/devices/1').json()['data']['controllable'] is True
        assert second.get('/api/devices/1').json()['data']['controllable'] is False


def test_raw_sql_binds_values_and_escapes_search_wildcards(client):
    client.app.state.mqtt.handle_message('esp32/sensor/data', '{"temperature":28.5,"light":1500}')
    for value in ['%', '_', '!', "' OR 1=1 --"]:
        result = client.get('/api/sensors/data', params={'value': value})
        assert result.status_code == 200 and result.json()['data']['totalElements'] == 0
    assert client.get('/api/sensors/data', params={'sensorType': "LIGHT' OR 1=1 --"}).json()['data']['totalElements'] == 0
    assert client.get('/api/history', params={'status': "SUCCESS' OR 1=1 --"}).json()['data']['totalElements'] == 0
    assert client.get('/api/history', params={'sort': 'desc; DELETE FROM users'}).status_code == 400
    assert client.post('/api/auth/login', json={'username': "admin' OR 1=1 --", 'password': 'wrong'}).status_code == 401
    name = "Nguyễn O'Connor; SELECT 1 --"
    body = registration_body(fullName=name)
    assert client.post('/api/auth/register', json=body).status_code == 201
    response = client.post('/api/auth/login', json={'username': body['username'], 'password': body['password']})
    assert response.status_code == 200 and response.json()['data']['fullName'] == name
    assert len(client.get('/api/devices').json()['data']) == 3


def test_raw_sql_logout_deletes_only_current_session(client):
    body = {'username': 'admin', 'password': '123456'}
    first = client.post('/api/auth/login', json=body).json()['data']['accessToken']
    second = client.post('/api/auth/login', json=body).json()['data']['accessToken']
    assert first != second
    client.headers['Authorization'] = f'Bearer {first}'
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/user/profile').status_code == 401
    client.headers['Authorization'] = f'Bearer {second}'
    assert client.get('/api/user/profile').status_code == 200


def test_chart_history_latest_30_times_all_sensors_and_partial_readings(client):
    start = datetime(2026, 10, 21, 12)
    with client.app.state.sessions.begin() as db:
        for index in range(35):
            for sensor_id in range(1, 5):
                if index == 34 and sensor_id == 1:
                    continue  # A DHT error must not turn into a fabricated zero.
                db.add(DataSensor(sensor_id=sensor_id, value=index * 10 + sensor_id,
                                  recorded_at=start + timedelta(seconds=index * 2, microseconds=sensor_id * 100)))
        # If multiple values exist in one second, keep the last recorded value.
        db.add(DataSensor(sensor_id=4, value=450, recorded_at=start + timedelta(seconds=68, microseconds=900)))
        other = Sensor(name='Unknown sensor', type='UNKNOWN', mqtt_key='unknown')
        db.add(other)
        db.flush()
        db.add(DataSensor(sensor_id=other.id, value=999, recorded_at=start + timedelta(days=1)))
    response = client.get('/api/sensors/chart')
    assert response.status_code == 200
    points = response.json()['data']
    assert len(points) == 30
    assert points[0] == {'time': '2026-10-21 12:00:10', 'temperature': 51, 'humidity': 52, 'light': 53, 'windSpeed': 54}
    assert points[-1] == {'time': '2026-10-21 12:01:08', 'humidity': 342, 'light': 343, 'windSpeed': 450}
    assert [point['time'] for point in points] == sorted(point['time'] for point in points)
    assert client.get('/api/sensors/chart?limit=2').json()['data'] == points[-2:]
