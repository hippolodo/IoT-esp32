from fastapi import APIRouter, Depends
from ..contracts import envelope
from ..dependencies import current_session, get_mqtt
from ..schemas import ThresholdRequest

router = APIRouter(prefix='/api/thresholds', tags=['Cảm biến'], dependencies=[Depends(current_session)])


# GET /api/thresholds: trả ngưỡng backend đang giữ và trạng thái ESP32 xác nhận.
@router.get('')
def thresholds(mqtt=Depends(get_mqtt)):
    return envelope(mqtt.threshold_status())


# POST /api/thresholds: nhận ba ngưỡng hợp lệ, gửi MQTT và trả trạng thái chờ xác nhận.
@router.post('')
def update_thresholds(body: ThresholdRequest, mqtt=Depends(get_mqtt)):
    return envelope(mqtt.set_thresholds(body.model_dump()), 'Đã gửi ngưỡng; chờ ESP32 xác nhận')
