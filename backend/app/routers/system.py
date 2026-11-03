from fastapi import APIRouter, Depends
from ..contracts import envelope
from ..dependencies import current_session, get_mqtt

router = APIRouter()


# GET /api/auth/health: kiểm tra HTTP backend đang chạy, không kiểm tra DB hay ESP32.
@router.get('/api/auth/health', tags=['Hệ thống'])
def health():
    return envelope('OK', 'Backend đang chạy')


# GET /api/system/status: trả trạng thái broker MQTT và ESP32 sau khi xác thực.
@router.get('/api/system/status', tags=['Hệ thống'], dependencies=[Depends(current_session)])
def system_status(mqtt=Depends(get_mqtt)):
    return envelope(mqtt.connection_status(), 'Trạng thái kết nối')
