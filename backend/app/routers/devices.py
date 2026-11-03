from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, current_user, database
from ..dependencies import get_mqtt, get_settings
from ..schemas import DeviceControlRequest
from ..services import devices as service

router = APIRouter()


# GET /api/alert-counts: trả tổng cảnh báo theo device ID đã lưu trong database.
@router.get('/api/alert-counts', tags=['Thiết bị'], dependencies=[Depends(current_session)])
def alert_counts(mqtt=Depends(get_mqtt)):
    return envelope(mqtt.alert_counts_status())


# GET /api/devices: trả danh sách đèn, trạng thái và khả năng điều khiển.
@router.get('/api/devices', tags=['Thiết bị'], dependencies=[Depends(current_session)])
def devices(db: Session = Depends(database), settings=Depends(get_settings)):
    result = service.devices(db=db, settings=settings)
    return envelope(result, 'Lấy danh sách thiết bị thành công')


# POST /api/devices/control: gửi lệnh qua service; HTTP OK chưa phải ACK của ESP32.
@router.post('/api/devices/control', tags=['Thiết bị'])
def control(
    body: DeviceControlRequest,
    user: dict = Depends(current_user),
    mqtt=Depends(get_mqtt),
):
    result = service.control(body=body, user=user, mqtt=mqtt)
    if body.status:
        message = 'Bật thiết bị thành công'
    else:
        message = 'Tắt thiết bị thành công'
    return envelope(result, message)


# GET /api/devices/{id}: trả thông tin một thiết bị hoặc lỗi 404.
@router.get('/api/devices/{id}', tags=['Thiết bị'], dependencies=[Depends(current_session)])
def device(id: int, db: Session = Depends(database), settings=Depends(get_settings)):
    result = service.device(id=id, db=db, settings=settings)
    return envelope(result, 'Lấy thông tin thiết bị thành công')
