import { api, websocketUrl, getAccessToken, expireSession } from '../api.js'
import { system, applyThresholds, emitSystemEvent } from './state.js'

const CONNECTION_REFRESH_MS = 5000
const WEBSOCKET_RETRY_MS = 3000
const MAX_CHART_POINTS = 30
const SENSOR_KEYS = ['temperature', 'humidity', 'light']

let socket,
  retry,
  poll,
  running = false,
  refreshing = null,
  checkingConnection = null
let sessionController = new AbortController()
let eventRevision = 0,
  deviceSequence = 0
let chartController,
  chartSequence = 0,
  chartHistoryLoaded = false

// A captured session stays invalid after stop/start, even if fetch finishes late.
// Chụp phiên đồng bộ hiện tại: signal để hủy request, isCurrent để chặn kết quả phiên cũ.
export function captureSystemSession() {
  const controller = sessionController
  return {
    signal: controller.signal,
    isCurrent: () => controller === sessionController && !controller.signal.aborted,
  }
}

// Hủy request thuộc phiên trước và tạo phiên mới mỗi khi start/stop hệ thống.
function renewSystemSession() {
  sessionController.abort()
  sessionController = new AbortController()
}

// Ghép các nhóm điểm theo cùng mốc giây, giữ giá trị hợp lệ và tối đa 30 điểm mới nhất.
function mergeChartPoints(...groups) {
  const points = new Map()
  for (const row of groups.flat()) {
    if (typeof row.time !== 'string') continue
    const time = row.time.slice(0, 19)
    const point = { ...points.get(time), time }
    for (const key of SENSOR_KEYS) {
      if (typeof row[key] === 'number' && Number.isFinite(row[key])) point[key] = row[key]
    }
    if (SENSOR_KEYS.some((key) => key in point)) points.set(time, point)
  }
  return [...points.values()].sort((a, b) => a.time.localeCompare(b.time)).slice(-MAX_CHART_POINTS)
}

// Gọi GET /api/sensors/chart?limit=30 rồi đưa lịch sử vào system.points.
// Giữ điểm realtime đến trong lúc chờ; request cũ hoặc phiên đã dừng không được ghi store.
export async function refreshChartHistory() {
  const session = captureSystemSession()
  chartController?.abort()
  const request = new AbortController()
  chartController = request
  const sequence = ++chartSequence
  system.chartLoading = true
  system.chartError = ''
  try {
    const history = await api('/api/sensors/chart', {
      query: { limit: MAX_CHART_POINTS },
      signal: AbortSignal.any([session.signal, request.signal]),
    })
    if (!running || !session.isCurrent() || sequence !== chartSequence) return
    // Keep realtime readings received while the database request was in flight.
    system.points = mergeChartPoints(history, system.points)
    chartHistoryLoaded = true
  } catch (error) {
    if (running && session.isCurrent() && sequence === chartSequence && error.name !== 'AbortError')
      system.chartError = error.message
  } finally {
    if (session.isCurrent() && sequence === chartSequence) system.chartLoading = false
  }
}

// values là object như {temperature: 35}, time là thời gian số đo từ API hoặc WebSocket.
// Lưu thành system.sensors.temperature = {value: 35, time}; bỏ số lỗi và dữ liệu cũ hơn.
function sensorValues(values, time) {
  for (const key of SENSOR_KEYS) {
    if (
      typeof values[key] === 'number' &&
      Number.isFinite(values[key]) &&
      (!system.sensors[key] || time >= system.sensors[key].time)
    )
      system.sensors[key] = { value: values[key], time }
  }
}

// Gọi GET /api/devices để cập nhật trạng thái/pending; tránh response cũ ghi đè sự kiện mới.
export async function refreshDevices() {
  const session = captureSystemSession()
  const sequence = ++deviceSequence,
    revision = eventRevision

      const devices = await api('/api/devices', { signal: session.signal })
  if (session.isCurrent() && sequence === deviceSequence && revision === eventRevision) system.devices = devices
}

// Lấy song song trạng thái kết nối, thiết bị, số đo mới nhất, ngưỡng và tổng cảnh báo.
// Chạy khi khởi động hoặc WebSocket kết nối lại; bỏ qua kết quả của phiên cũ.
export async function refreshSystem() {
  if (refreshing?.isCurrent()) return
  const session = captureSystemSession()
  refreshing = session
  try {
    // Ghi phiên bản sự kiện trước request; có WebSocket mới thì không ghi đè bằng snapshot này.
    const revision = eventRevision
    // Kết quả thứ ba lưu vào latest; bỏ kết quả thứ hai vì refreshDevices tự cập nhật store.
    const [status, , latest, thresholds, alertCounts] = await Promise.all([
      api('/api/system/status', { signal: session.signal }),
      refreshDevices(),
      api('/api/sensors/latest', { signal: session.signal }),
      api('/api/thresholds', { signal: session.signal }),
      api('/api/alert-counts', { signal: session.signal }),
    ])
    if (!running || !session.isCurrent()) return
    Object.assign(system, { backendOnline: true, error: '' })
    if (revision === eventRevision) Object.assign(system, status)
    if (revision === eventRevision) applyThresholds(thresholds)
    if (revision === eventRevision) system.alertCounts = alertCounts
    // row là một số đo API; TEMPERATURE đổi thành temperature, recordedAt được truyền làm time.
    latest.forEach((row) => sensorValues({
      [row.sensorType.toLowerCase()]: row.value,
    }, row.recordedAt))
  } catch (error) {
    if (running && session.isCurrent())
      Object.assign(system, {
        backendOnline: false,
        mqttConnected: false,
        esp32Online: null,
        error: error.message,
      })
  } finally {
    if (refreshing === session) refreshing = null
  }
}

// Chỉ kiểm tra kết nối định kỳ để phát hiện MQTT/ESP32 offline theo timeout backend.
async function refreshConnectionStatus() {
  if (checkingConnection?.isCurrent() || refreshing?.isCurrent()) return
  const session = captureSystemSession()
  checkingConnection = session
  const revision = eventRevision
  try {
    const status = await api('/api/system/status', { signal: session.signal })
    if (!running || !session.isCurrent()) return
    Object.assign(system, { backendOnline: true, error: '' })
    if (revision === eventRevision) Object.assign(system, status)
  } catch (error) {
    if (running && session.isCurrent())
      Object.assign(system, {
        backendOnline: false,
        mqttConnected: false,
        esp32Online: null,
        error: error.message,
      })
  } finally {
    if (checkingConnection === session) checkingConnection = null
  }
}

// Nhận /topic/sensors: cập nhật số đo, lỗi DHT và thêm điểm realtime vào biểu đồ.
function handleSensorEvent(event) {
  const time = event.recordedAt || new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' })
  sensorValues(event.data, time)
  system.sensorError = event.data.error || ''
  system.esp32Online = true
  system.mqttConnected = true
  system.points = mergeChartPoints(system.points, [{ time, ...event.data }])
}

// Nhận ACK/timeout của đèn, cập nhật trạng thái rồi lấy lại danh sách để đồng bộ pending.
function handleDeviceEvent(event) {
  const session = captureSystemSession()
  const device = system.devices.find((row) => row.id === event.data.deviceId)
  if (device && event.data.status != null) device.status = event.data.status
  if (['FAIL', 'TIMEOUT'].includes(event.data.result))
    system.controlError = 'Thiết bị không xác nhận được lệnh. Vui lòng kiểm tra mạch.'
  refreshDevices().catch((error) => {
    if (session.isCurrent()) system.error = error.message
  })
}

// Đọc JSON từ WebSocket và chuyển từng topic đến đúng phần cập nhật store.
function handleSocketMessage(data) {
  let event
  try {
    event = JSON.parse(data)
  } catch {
    return
  }
  if (event.type === 'authenticated') {
    system.realtime = true
    refreshSystem()
    if (!system.chartLoading) refreshChartHistory()
    return
  }
  eventRevision++
  if (event.topic === '/topic/sensors') {
    handleSensorEvent(event)
  } else if (event.topic === '/topic/thresholds') {
    applyThresholds(event.data)
  } else if (event.topic === '/topic/alert-counts') {
    system.alertCounts = event.data
  } else if (event.topic === '/topic/device-status') {
    handleDeviceEvent(event)
  } else if (event.topic === '/topic/esp32-status') {
    system.esp32Online = event.data.message.includes('STATUS: ONLINE')
  }
  emitSystemEvent(event)
}

// Mở WebSocket, gửi token ở bản tin đầu; mất kết nối thì thử lại sau 3 giây.
// Đóng với mã 4401 nghĩa là phiên không hợp lệ, cần quay về đăng nhập.
function connect(session = captureSystemSession()) {
  if (!running || !session.isCurrent()) return
  const connection = new WebSocket(websocketUrl())
  socket = connection
  connection.onopen = () => {
    if (!running || !session.isCurrent() || socket !== connection) return
    connection.send(JSON.stringify({ type: 'auth', token: getAccessToken() }))
  }
  connection.onmessage = ({ data }) => {
    if (!running || !session.isCurrent() || socket !== connection) return
    handleSocketMessage(data)
  }
  connection.onclose = ({ code } = {}) => {
    if (!session.isCurrent() || socket !== connection) return
    system.realtime = false
    if (running && code === 4401) {
      expireSession()
      return
    }
    if (running) retry = setTimeout(() => connect(session), WEBSOCKET_RETRY_MS)
  }
  connection.onerror = () => connection.close()
}

// Lấy snapshot ban đầu, nhận cập nhật qua WebSocket và chỉ kiểm tra kết nối định kỳ.
export function startSystem() {
  if (running) return
  renewSystemSession()
  running = true
  chartHistoryLoaded = false
  refreshSystem()
  refreshChartHistory()
  connect()
  poll = setInterval(() => {
    refreshConnectionStatus()
    if (!chartHistoryLoaded && !system.chartLoading) refreshChartHistory()
  }, CONNECTION_REFRESH_MS)
}

// Dừng polling/reconnect, hủy request và đóng socket để phiên cũ không cập nhật giao diện.
export function stopSystem() {
  running = false
  renewSystemSession()
  chartSequence++
  chartController?.abort()
  system.chartLoading = false
  clearTimeout(retry)
  clearInterval(poll)
  system.realtime = false
  const connection = socket
  socket = undefined
  connection?.close()
}

