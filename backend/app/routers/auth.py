from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, current_user, database, get_registration_lock
from ..schemas import LoginRequest, RegisterRequest
from ..services import auth as service

router = APIRouter()


@router.post('/api/auth/register', status_code=201, tags=['Xác thực'])
def register(
    body: RegisterRequest,
    db: Session = Depends(database),
    registration_lock=Depends(get_registration_lock),
):
    result = service.register(body=body, db=db, registration_lock=registration_lock)
    return envelope(result, 'Đăng ký tài khoản thành công. Vui lòng đăng nhập.', code=201)


@router.post('/api/auth/login', tags=['Xác thực'])
def login(body: LoginRequest, db: Session = Depends(database)):
    result = service.login(body=body, db=db)
    return envelope(result, 'Đăng nhập thành công')


@router.post('/api/auth/logout', tags=['Xác thực'])
def logout(session: dict = Depends(current_session), db: Session = Depends(database)):
    result = service.logout(session=session, db=db)
    return envelope(result, 'Đã đăng xuất')


@router.get('/api/user/profile', tags=['Người dùng'])
def profile(user: dict = Depends(current_user)):
    result = service.profile(user=user)
    return envelope(result, 'Lấy thông tin user thành công')
