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
  error: '',
  sensorError: '',
  controlError: '',
  sending: {},
  sendingAll: false,
})
const listeners = new Set()
let socket,
  retry,
  poll,
  running = false,
  refreshing = false
let eventRevision = 0,
  deviceSequence = 0

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
    const [status, , latest] = await Promise.all([
      api('/api/system/status'),
      refreshDevices(),
      api('/api/sensors/latest'),
    ])
    if (!running) return
    Object.assign(system, { backendOnline: true, error: '' })
    if (revision === eventRevision) Object.assign(system, status)
    latest.forEach((row) => sensorValues({ [row.sensorType.toLowerCase()]: row.value }, row.recordedAt))
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
      return
    }
    eventRevision++
    if (event.topic === '/topic/sensors') {
      const time = new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' })
      sensorValues(event.data, time)
      system.sensorError = event.data.error || ''
      system.esp32Online = true
      system.mqttConnected = true
      system.points = [...system.points, { time, ...event.data }].slice(-MAX_CHART_POINTS)
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
  refreshSystem()
  connect()
  poll = setInterval(refreshSystem, SYSTEM_REFRESH_MS)
}

export function stopSystem() {
  running = false
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
  const devices = system.devices.filter((device) => device.id !== 3 && device.controllable)
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
