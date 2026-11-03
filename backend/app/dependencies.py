"""Request dependencies resolved from the current app instance."""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .services.auth import authenticate_token, get_user

bearer_auth = HTTPBearer(auto_error=False, description="Dán accessToken nhận từ /api/auth/login để xác thực.")


# Cấp Session cho một request và tự đóng sau khi request kết thúc.
def database(request: Request):
    with request.app.state.sessions() as db:
        yield db


# Đọc Bearer token từ request, kiểm tra phiên và trả thông tin phiên đăng nhập.
def current_session(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth),
                    db: Session = Depends(database)):
    if credentials:
        token = credentials.credentials
    else:
        token = None
    return authenticate_token(token, db)


# Lấy tài khoản của phiên đã xác thực; không tin userId do frontend tự gửi.
def current_user(session: dict = Depends(current_session), db: Session = Depends(database)):
    return get_user(session['user_id'], db)


# Lấy MqttService thuộc app đang xử lý request để router gọi nghiệp vụ MQTT.
def get_mqtt(request: Request):
    return request.app.state.mqtt


# Lấy cấu hình của app hiện tại cho các endpoint cần ánh xạ thiết bị.
def get_settings(request: Request):
    return request.app.state.settings


# Lấy khóa dùng chung trong tiến trình để tuần tự hóa việc đăng ký tài khoản.
def get_registration_lock(request: Request):
    return request.app.state.registration_lock
