"""Account registration, sessions and token validation."""
import hashlib
import re
import secrets
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..contracts import ControlError, as_datetime, execute_sql, now
from ..schemas import LoginRequest, RegisterRequest
from ..passwords import hash_password, verify_password

SESSION_LIFETIME = timedelta(hours=24)


def authenticate_token(token, db: Session):
    if not isinstance(token, str) or not token:
        raise ControlError("Vui lòng đăng nhập để tiếp tục", 401)
    session = execute_sql(db, """
        SELECT a.token_hash, a.user_id, a.expires_at
        FROM auth_sessions AS a
        JOIN users AS u ON u.id = a.user_id
        WHERE a.token_hash = :token_hash
    """, {'token_hash': hashlib.sha256(token.encode()).hexdigest()}).mappings().first()
    if session is None or as_datetime(session['expires_at']) <= now():
        raise ControlError("Vui lòng đăng nhập để tiếp tục", 401)
    return dict(session)


def get_user(user_id, db: Session):
    row = execute_sql(db, "SELECT * FROM users WHERE id = :id", {'id': user_id}).mappings().first()
    if row is None:
        raise ControlError("Vui lòng đăng nhập để tiếp tục", 401)
    return dict(row)


def register(body: RegisterRequest, db: Session, registration_lock):
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
        if execute_sql(db, "SELECT id FROM users WHERE LOWER(username) = :username LIMIT 1",
                       {'username': username}).first() is not None:
            raise ControlError("Tên đăng nhập đã được sử dụng", 409)
        if execute_sql(db, "SELECT id FROM users WHERE LOWER(email) = :email LIMIT 1",
                       {'email': email}).first() is not None:
            raise ControlError("Email đã được sử dụng", 409)
        try:
            result = execute_sql(db, """
                INSERT INTO users (username, full_name, email, password_hash, created_at)
                VALUES (:username, :full_name, :email, :password_hash, :created_at)
            """, {'username': username, 'full_name': full_name, 'email': email,
                  'password_hash': hash_password(body.password), 'created_at': now()})
            user_id = result.lastrowid
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ControlError("Tên đăng nhập hoặc email đã được sử dụng", 409) from None
    return dict(userId=user_id, username=username, fullName=full_name, email=email)


def login(body: LoginRequest, db: Session):
    if not body.username:
        raise ControlError("Username không được để trống", 400)
    if not body.password:
        raise ControlError("Password không được để trống", 400)
    username = body.username.strip().lower()
    user = execute_sql(db, "SELECT * FROM users WHERE LOWER(username) = :username LIMIT 1",
                       {'username': username}).mappings().first()
    if not user or not verify_password(body.password, user['password_hash']):
        raise ControlError("Sai tài khoản hoặc mật khẩu", 401)
    token = secrets.token_urlsafe(32)
    execute_sql(db, """
        INSERT INTO auth_sessions (token_hash, user_id, expires_at)
        VALUES (:token_hash, :user_id, :expires_at)
    """, {'token_hash': hashlib.sha256(token.encode()).hexdigest(),
          'user_id': user['id'], 'expires_at': now() + SESSION_LIFETIME})
    db.commit()
    return dict(userId=user['id'], username=user['username'], fullName=user['full_name'], accessToken=token,
                email=user['email'], success=True, message="Đăng nhập thành công")


def logout(session: dict, db: Session):
    execute_sql(db, "DELETE FROM auth_sessions WHERE token_hash = :token_hash",
                {'token_hash': session['token_hash']})
    db.commit()
    return "OK"


def profile(user: dict):
    return dict(id=user['id'], username=user['username'], fullName=user['full_name'], email=user['email'],
                createdAt=as_datetime(user['created_at']).isoformat() if user['created_at'] else None)


def websocket_session_valid(token, sessions):
    with sessions() as db:
        try:
            authenticate_token(token, db)
            return True
        except ControlError:
            return False
