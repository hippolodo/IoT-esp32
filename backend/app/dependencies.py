"""Request dependencies resolved from the current app instance."""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .services.auth import authenticate_token, get_user

bearer_auth = HTTPBearer(auto_error=False, description="Dán accessToken nhận từ /api/auth/login để xác thực.")


def database(request: Request):
    with request.app.state.sessions() as db:
        yield db


def current_session(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth),
                    db: Session = Depends(database)):
    return authenticate_token(credentials.credentials if credentials else None, db)


def current_user(session: dict = Depends(current_session), db: Session = Depends(database)):
    return get_user(session['user_id'], db)


def get_mqtt(request: Request):
    return request.app.state.mqtt


def get_settings(request: Request):
    return request.app.state.settings


def get_registration_lock(request: Request):
    return request.app.state.registration_lock
