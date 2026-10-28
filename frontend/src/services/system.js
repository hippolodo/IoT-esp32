import { reactive } from 'vue'
import { api, websocketUrl, getAccessToken, expireSession } from './api.js'

const SYSTEM_REFRESH_MS = 5000
const WEBSOCKET_RETRY_MS = 3000
const MAX_CHART_POINTS = 30
const SENSOR_KEYS = ['temperature', 'humidity', 'light']

export const system = reactive({
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
})
const listeners = new Set()
let socket,
  retry,
  poll,
  running = false,
  refreshing = false
let eventRevision = 0,
  deviceSequence = 0
let chartController,
  chartSequence = 0,
  chartHistoryLoaded = false

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
  chartController?.abort()
  const request = new AbortController()
  chartController = request
  const sequence = ++chartSequence
  system.chartLoading = true
  system.chartError = ''
  try {
    const history = await api('/api/sensors/chart', {
      query: { limit: MAX_CHART_POINTS },
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(10000)]),
    })
    if (!running || sequence !== chartSequence) return
    // Keep realtime readings received while the database request was in flight.
    system.points = mergeChartPoints(history, system.points)
    chartHistoryLoaded = true
  } catch (error) {
    if (running && sequence === chartSequence && error.name !== 'AbortError') system.chartError = error.message
  } finally {
    if (sequence === chartSequence) system.chartLoading = false
  }
}

export function onSystemEvent(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
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
  const sequence = ++deviceSequence,
    revision = eventRevision
  const devices = await api('/api/devices')
  if (sequence === deviceSequence && revision === eventRevision) system.devices = devices
}

export async function refreshSystem() {
  if (refreshing) return
  refreshing = true
  try {
    const revision = eventRevision
    const [status, , latest, thresholds, alertCounts] = await Promise.all([
      api('/api/system/status'),
      refreshDevices(),
      api('/api/sensors/latest'),
      api('/api/thresholds'),
      api('/api/alert-counts'),
    ])
    if (!running) return
    Object.assign(system, { backendOnline: true, error: '' })
    if (revision === eventRevision) Object.assign(system, status)
    if (revision === eventRevision) applyThresholds(thresholds)
    if (revision === eventRevision) system.alertCounts = alertCounts
    latest.forEach((row) => sensorValues({
      [row.sensorType.toLowerCase()]: row.value,
    }, row.recordedAt))
  } catch (error) {
    if (running)
      Object.assign(system, {
        backendOnline: false,
        mqttConnected: false,
        esp32Online: null,
        error: error.message,
      })
  } finally {
    refreshing = false
  }
}

function connect() {
  if (!running) return
  const connection = new WebSocket(websocketUrl())
  socket = connection
  connection.onopen = () => {
    if (!running || socket !== connection) return
    connection.send(JSON.stringify({ type: 'auth', token: getAccessToken() }))
  }
  connection.onmessage = ({ data }) => {
    if (!running || socket !== connection) return
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
      const time = event.recordedAt || new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' })
      sensorValues(event.data, time)
      system.sensorError = event.data.error || ''
      system.esp32Online = true
      system.mqttConnected = true
      system.points = mergeChartPoints(system.points, [{ time, ...event.data }])
    } else if (event.topic === '/topic/thresholds') {
      applyThresholds(event.data)
    } else if (event.topic === '/topic/alert-counts') {
      system.alertCounts = event.data
    } else if (event.topic === '/topic/device-status') {
      const device = system.devices.find((row) => row.id === event.data.deviceId)
      if (device && event.data.status != null) device.status = event.data.status
      if (['FAIL', 'TIMEOUT'].includes(event.data.result))
        system.controlError = 'Thiết bị không xác nhận được lệnh. Vui lòng kiểm tra mạch.'
      refreshDevices().catch((error) => {
        system.error = error.message
      })
    } else if (event.topic === '/topic/esp32-status') {
      system.esp32Online = event.data.message.includes('STATUS: ONLINE')
    }
    listeners.forEach((listener) => listener(event))
  }
  connection.onclose = ({ code } = {}) => {
    if (socket !== connection) return
    system.realtime = false
    if (running && code === 4401) {
      expireSession()
      return
    }
    if (running) retry = setTimeout(connect, WEBSOCKET_RETRY_MS)
  }
  connection.onerror = () => connection.close()
}

export function startSystem() {
  if (running) return
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
  chartSequence++
  chartController?.abort()
  system.chartLoading = false
  clearTimeout(retry)
  clearInterval(poll)
  system.realtime = false
  socket?.close()
}

export async function toggleDevice(device) {
  if (system.sendingAll || system.sending[device.id] || device.pending) return
  system.sending[device.id] = true
  system.controlError = ''
  try {
    await api('/api/devices/control', {
      method: 'POST',
      body: JSON.stringify({ deviceId: device.id, status: device.status === 1 ? 0 : 1 }),
    })
    await refreshDevices()
    listeners.forEach((listener) =>
      listener({ topic: '/topic/device-status', data: { deviceId: device.id } }),
    )
  } catch (error) {
    system.controlError = error.message
  } finally {
    delete system.sending[device.id]
  }
}

export async function controlAllDevices(status) {
  const devices = system.devices.filter((device) => device.controllable)
  if (
    ![0, 1].includes(status) ||
    system.sendingAll ||
    !system.backendOnline ||
    !system.mqttConnected ||
    system.esp32Online !== true ||
    devices.some((device) => device.pending || system.sending[device.id])
  ) return

  const targets = devices.filter((device) => device.status !== status)
  if (!targets.length) return
  system.sendingAll = true
  system.controlError = ''
  targets.forEach((device) => { system.sending[device.id] = true })
  try {
    const results = await Promise.allSettled(targets.map(async (device) => {
      await api('/api/devices/control', {
        method: 'POST',
        body: JSON.stringify({ deviceId: device.id, status }),
      })
    }))
    const errors = results.flatMap((result, index) =>
      result.status === 'rejected'
        ? [`${targets[index].name}: ${result.reason.message}`]
        : [],
    )
    if (errors.length) system.controlError = errors.join('; ')
    // Refresh pending/confirmed states; do not assume HTTP success means the LED changed.
    await refreshDevices()
    listeners.forEach((listener) => listener({ topic: '/topic/device-status', data: {} }))
  } catch (error) {
    system.controlError = [system.controlError, error.message].filter(Boolean).join('; ')
  } finally {
    targets.forEach((device) => { delete system.sending[device.id] })
    system.sendingAll = false
  }
}

function applyThresholds(data) {
  system.thresholds = data.values
  system.thresholdConfirmed = data.confirmed
}

export async function saveThresholds(values) {
  applyThresholds(await api('/api/thresholds', { method: 'POST', body: JSON.stringify(values) }))
}
