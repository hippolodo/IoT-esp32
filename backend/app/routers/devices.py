from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..contracts import envelope
from ..dependencies import current_session, current_user, database
from ..dependencies import get_mqtt, get_settings
from ..schemas import DeviceControlRequest
from ..services import devices as service

router = APIRouter()


@router.get('/api/alert-counts', tags=['Thiết bị'], dependencies=[Depends(current_session)])
def alert_counts(mqtt=Depends(get_mqtt)):
    return envelope(mqtt.alert_counts_status())


@router.get('/api/devices', tags=['Thiết bị'], dependencies=[Depends(current_session)])
def devices(db: Session = Depends(database), settings=Depends(get_settings)):
    result = service.devices(db=db, settings=settings)
    return envelope(result, 'Lấy danh sách thiết bị thành công')


@router.post('/api/devices/control', tags=['Thiết bị'])
def control(
    body: DeviceControlRequest,
    user: dict = Depends(current_user),
    mqtt=Depends(get_mqtt),
):
    result = service.control(body=body, user=user, mqtt=mqtt)
    return envelope(result, 'Bật thiết bị thành công' if body.status else 'Tắt thiết bị thành công')


@router.get('/api/devices/{id}', tags=['Thiết bị'], dependencies=[Depends(current_session)])
def device(id: int, db: Session = Depends(database), settings=Depends(get_settings)):
    result = service.device(id=id, db=db, settings=settings)
    return envelope(result, 'Lấy thông tin thiết bị thành công')
