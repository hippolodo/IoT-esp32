from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, database
from ..services import alerts as service

router = APIRouter()


@router.get(
    '/api/alerts/wind/summary',
    tags=['Cảnh báo gió'],
    dependencies=[Depends(current_session)],
)
def wind_summary(month: str, db: Session = Depends(database)):
    result = service.wind_summary(month=month, db=db)
    return envelope(result)


@router.get('/api/alerts/wind', tags=['Cảnh báo gió'], dependencies=[Depends(current_session)])
def wind_alerts(date: str, page: int = 0, size: int = 10, db: Session = Depends(database)):
    result = service.wind_alerts(date=date, page=page, size=size, db=db)
    return envelope(result)
