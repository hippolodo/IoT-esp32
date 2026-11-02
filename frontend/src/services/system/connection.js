import { api, websocketUrl, getAccessToken, expireSession } from '../api.js'
import { system, applyThresholds, emitSystemEvent } from './state.js'

const SYSTEM_REFRESH_MS = 5000
const WEBSOCKET_RETRY_MS = 3000
const MAX_CHART_POINTS = 30
const SENSOR_KEYS = ['temperature', 'humidity', 'light']

let socket,
  retry,
  poll,
  running = false,
  refreshing = null
let sessionController = new AbortController()
let eventRevision = 0,
  deviceSequence = 0
let chartController,
  chartSequence = 0,
  chartHistoryLoaded = false

// A captured session stays invalid after stop/start, even if fetch finishes late.
export function captureSystemSession() {
  const controller = sessionController
  return {
    signal: controller.signal,
    isCurrent: () => controller === sessionController && !controller.signal.aborted,
  }
}

function renewSystemSession() {
  sessionController.abort()
  sessionController = new AbortController()
}

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

export async function refreshDevices() {
  const session = captureSystemSession()
  const sequence = ++deviceSequence,
    revision = eventRevision
  const devices = await api('/api/devices', { signal: session.signal })
  if (session.isCurrent() && sequence === deviceSequence && revision === eventRevision) system.devices = devices
}

export async function refreshSystem() {
  if (refreshing?.isCurrent()) return
  const session = captureSystemSession()
  refreshing = session
  try {
    const revision = eventRevision
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

function handleSensorEvent(event) {
  const time = event.recordedAt || new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' })
  sensorValues(event.data, time)
  system.sensorError = event.data.error || ''
  system.esp32Online = true
  system.mqttConnected = true
  system.points = mergeChartPoints(system.points, [{ time, ...event.data }])
}

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

export function startSystem() {
  if (running) return
  renewSystemSession()
  running = true
  chartHistoryLoaded = false
  refreshSystem()
  refreshChartHistory()
  connect()
  poll = setInterval(() => {
    refreshSystem()
    if (!chartHistoryLoaded && !system.chartLoading) refreshChartHistory()
  }, SYSTEM_REFRESH_MS)
}

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

