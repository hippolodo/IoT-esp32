from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, database
from ..services import history as service

router = APIRouter()


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
    deviceType: str | None = None,
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
        deviceType=deviceType,
        db=db,
    )
    return envelope(
        result,
        'Lấy lịch sử cảnh báo thành công' if deviceType is not None else 'Lấy lịch sử thành công',
    )


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
