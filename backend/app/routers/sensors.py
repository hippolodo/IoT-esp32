from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, database
from ..services import sensors as service

router = APIRouter()


# GET /api/sensors: trả danh mục các cảm biến được hỗ trợ.
@router.get('/api/sensors', tags=['Cảm biến'], dependencies=[Depends(current_session)])
def sensors(db: Session = Depends(database)):
    result = service.sensors(db=db)
    return envelope(result, 'Lấy danh sách cảm biến thành công')


# GET /api/sensors/latest: lấy số đo mới nhất từ DB để Dashboard có REST snapshot.
@router.get('/api/sensors/latest', tags=['Cảm biến'], dependencies=[Depends(current_session)])
def latest(db: Session = Depends(database)):
    result = service.latest(db=db)
    return envelope(result, 'Lấy dữ liệu cảm biến gần đây thành công')


# GET /api/sensors/chart: lấy tối đa 30 mốc dữ liệu lịch sử cho biểu đồ.
@router.get('/api/sensors/chart', tags=['Cảm biến'], dependencies=[Depends(current_session)])
def sensor_chart(limit: int = 30, db: Session = Depends(database)):
    result = service.sensor_chart(limit=limit, db=db)
    return envelope(result, 'Lấy lịch sử biểu đồ thành công')


# GET /api/sensors/data: chuyển bộ lọc và phân trang sang service tra cứu số đo.
@router.get('/api/sensors/data', tags=['Cảm biến'], dependencies=[Depends(current_session)])
def sensor_data(
    sensorId: int | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    page: int = 0,
    size: int = 10,
    sensorType: str | None = None,
    value: str | None = None,
    db: Session = Depends(database),
):
    result = service.sensor_data(
        sensorId=sensorId,
        startTime=startTime,
        endTime=endTime,
        page=page,
        size=size,
        sensorType=sensorType,
        value=value,
        db=db,
    )
    return envelope(result, 'Lấy dữ liệu cảm biến thành công')
