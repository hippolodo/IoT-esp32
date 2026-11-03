from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, database
from ..services import history as service

router = APIRouter()


# GET /api/history: tra cứu lịch sử điều khiển/cảnh báo với bộ lọc, sort và phân trang.
@router.get('/api/history', tags=['Lịch sử'], dependencies=[Depends(current_session)])
def history(
    deviceId: int | None = None,
    status: str | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    page: int = 0,
    size: int = 10,
    action: str | None = None,
    sort: str = 'desc',
    db: Session = Depends(database),
):
    result = service.history(
        deviceId=deviceId,
        status=status,
        startTime=startTime,
        endTime=endTime,
        page=page,
        size=size,
        action=action,
        sort=sort,
        db=db,
    )
    return envelope(result, 'Lấy lịch sử thành công')


# GET /api/history/filter: lọc lịch sử theo tham số của endpoint cũ.
@router.get('/api/history/filter', tags=['Lịch sử'], dependencies=[Depends(current_session)])
def filter_history(
    deviceId: int | None = None,
    status: str | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    page: int = 0,
    size: int = 10,
    db: Session = Depends(database),
):
    result = service.filter_history(
        deviceId=deviceId,
        status=status,
        startTime=startTime,
        endTime=endTime,
        page=page,
        size=size,
        db=db,
    )
    return envelope(result, 'Lọc lịch sử thành công')
