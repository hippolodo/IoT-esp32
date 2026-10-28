from fastapi import APIRouter, Depends
from ..contracts import envelope
from ..dependencies import current_session, get_mqtt
from ..schemas import ThresholdRequest

router = APIRouter(prefix='/api/thresholds', tags=['Cảm biến'], dependencies=[Depends(current_session)])


@router.get('')
def thresholds(mqtt=Depends(get_mqtt)):
    return envelope(mqtt.threshold_status())


@router.post('')
def update_thresholds(body: ThresholdRequest, mqtt=Depends(get_mqtt)):
    return envelope(mqtt.set_thresholds(body.model_dump()), 'Đã gửi ngưỡng; chờ ESP32 xác nhận')
