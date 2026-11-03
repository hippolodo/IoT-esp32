import { reactive } from 'vue'

// Tạo bộ giá trị mặc định mới; các object/array không dùng chung với phiên trước.
function createInitialState() {
  return {
    backendOnline: false,
    realtime: false,
    mqttConnected: false,
    esp32Online: null,
    devices: [],
    sensors: {},
    points: [],
    chartLoading: false,
    chartError: '',
    error: '',
    sensorError: '',
    controlError: '',
    sending: {},
    sendingAll: false,
    thresholds: {},
    thresholdConfirmed: {},
    alertCounts: {},
  }
}

// Store phản ứng dùng chung: component đọc ở đây; REST/WebSocket cập nhật thì Vue tự render lại.
export const system = reactive(createInitialState())
const listeners = new Set()

// Xóa dữ liệu của phiên cũ nhưng giữ nguyên object reactive mà component đã import.
export function resetSystemState() {
  Object.assign(system, createInitialState())
}

// Đăng ký hàm nghe sự kiện nội bộ; trả hàm hủy đăng ký để dùng khi unmount.
export function onSystemEvent(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

// Báo các màn hình đang nghe tải lại dữ liệu; không gửi API hay MQTT từ hàm này.
export function emitSystemEvent(event) {
  listeners.forEach((listener) => listener(event))
}

// Lưu values và confirmed từ API/WebSocket vào store để form ngưỡng cùng đọc.
export function applyThresholds(data) {
  system.thresholds = data.values
  system.thresholdConfirmed = data.confirmed
}
