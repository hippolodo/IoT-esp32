import test from 'node:test'
import assert from 'node:assert/strict'
import { api, websocketUrl, setAccessToken } from '../src/services/api.js'
import { system, startSystem, stopSystem, toggleDevice, controlAllDevices } from '../src/services/system.js'

const tick = () => new Promise(resolve => setImmediate(resolve))
const ok = data => ({ ok: true, json: async () => ({ success: true, data }) })

test('bulk control sends explicit states, prevents duplicates and reports partial failure', async () => {
  const devices = [
    { id: 1, name: 'LED 1', status: 0, controllable: true, pending: false },
    { id: 2, name: 'LED 2', status: 0, controllable: true, pending: false },
    { id: 3, name: 'Unmapped', status: 0, controllable: false, pending: false },
    { id: 4, name: 'Already on', status: 1, controllable: true, pending: false },
  ]
  Object.assign(system, { devices, backendOnline: true, mqttConnected: true, esp32Online: true })
  const posted = []
  let release
  const gate = new Promise(resolve => { release = resolve })
  globalThis.fetch = async (url, options) => {
    if (url === '/api/devices') return ok(devices)
    const command = JSON.parse(options.body)
    posted.push(command)
    await gate
    if (command.deviceId === 2)
      return { ok: false, status: 503, json: async () => ({ message: 'MQTT offline' }) }
    devices[0].pending = true
    return ok('OK')
  }
  const request = controlAllDevices(1)
  assert.equal(system.sendingAll, true)
  await controlAllDevices(0)
  await toggleDevice(devices[1])
  assert.deepEqual(posted, [{ deviceId: 1, status: 1 }, { deviceId: 2, status: 1 }])
  release()
  await request
  assert.match(system.controlError, /LED 2: MQTT offline/)
  assert.equal(system.devices[0].status, 0, 'wait for physical ACK')
  assert.equal(system.devices[0].pending, true)
  assert.equal(system.sendingAll, false)
  assert.deepEqual(system.sending, {})
  await controlAllDevices(0)
  assert.equal(posted.length, 2, 'pending command blocks bulk control')

  devices[0].pending = false
  globalThis.fetch = async (url, options) => {
    if (url === '/api/devices') return ok(devices)
    posted.push(JSON.parse(options.body))
    return ok('OK')
  }
  await controlAllDevices(0)
  assert.deepEqual(posted.at(-1), { deviceId: 4, status: 0 })
  system.devices = []
})

test('API sends session token and clears it after unauthorized response', async () => {
  let headers
  globalThis.fetch = async (url, options) => { headers = options.headers; return ok('OK') }
  setAccessToken('session-token')
  await api('/api/devices/control', { method: 'POST', body: '{}' })
  assert.equal(headers.Authorization, 'Bearer session-token')
  globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ message: 'Đăng nhập lại' }) })
  await assert.rejects(api('/api/user/profile'), /Đăng nhập lại/)
  globalThis.fetch = async (url, options) => { headers = options.headers; return ok('OK') }
  await api('/api/auth/login')
  assert.equal(headers.Authorization, undefined)
})

test('API preserves filters, POST body and server errors', async () => {
  let received
  globalThis.fetch = async (url, options) => { received = { url, options }; return ok([]) }
  await api('/api/history', { query: { page: 1, deviceId: 2, status: undefined, action: 'ON' } })
  assert.equal(received.url, '/api/history?page=1&deviceId=2&action=ON')
  await api('/api/devices/control', { method: 'POST', body: JSON.stringify({ deviceId: 1, status: 1 }) })
  assert.equal(received.options.body, '{"deviceId":1,"status":1}')
  globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ message: 'MQTT offline' }) })
  await assert.rejects(api('/api/devices/control'), /MQTT offline/)
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(api('/api/devices'), /8088/)
})

test('dashboard loads real snapshot, waits for ACK, handles timeout and reconnects', async () => {
  globalThis.window = { location: { origin: 'http://localhost:5173' } }
  assert.equal(websocketUrl(), 'ws://localhost:5173/ws')
  const instances = []
  setAccessToken('websocket-session-token')
  globalThis.WebSocket = class {
    constructor(url) { this.url = url; instances.push(this) }
    send(message) { this.sent = JSON.parse(message) }
    close(code = 1000) { this.onclose?.({ code }) }
    event(topic, data) { this.onmessage({ data: JSON.stringify({ topic, data }) }) }
  }
  let status = 0, pending = false, posted
  globalThis.fetch = async (url, options) => {
    if (url === '/api/system/status') return ok({ mqttConnected: true, esp32Online: true })
    if (url === '/api/devices') return ok([{ id: 1, name: 'LED', status, controllable: true, pending }])
    if (url === '/api/sensors/latest') return ok([{ sensorType: 'temperature', value: 25, recordedAt: '2026-01-01 00:00:00' }])
    if (url === '/api/devices/control') { posted = JSON.parse(options.body); pending = true; return ok('OK') }
    throw new Error(`Unexpected request: ${url}`)
  }
  try {
    startSystem()
    await tick()
    const ws = instances[0]
    ws.onopen()
    assert.deepEqual(ws.sent, { type: 'auth', token: 'websocket-session-token' })
    assert.equal(ws.url, 'ws://localhost:5173/ws', 'token must not appear in URL')
    assert.equal(system.realtime, false, 'wait for server authentication acknowledgment')
    ws.onmessage({ data: JSON.stringify({ type: 'authenticated' }) })
    await tick()
    assert.equal(system.backendOnline, true)
    assert.equal(system.sensors.temperature.value, 25)
    ws.event('/topic/sensors', { temperature: 30, humidity: 60, light: 1234 })
    assert.equal(system.points.at(-1).light, 1234)
    assert.equal(system.sensors.temperature.value, 30)
    await toggleDevice(system.devices[0])
    assert.deepEqual(posted, { deviceId: 1, status: 1 })
    assert.equal(system.devices[0].status, 0)
    assert.equal(system.devices[0].pending, true)
    status = 1; pending = false
    ws.event('/topic/device-status', { deviceId: 1, status: 1, result: 'ON' })
    await tick()
    assert.equal(system.devices[0].status, 1)
    assert.equal(system.devices[0].pending, false)
    ws.event('/topic/device-status', { deviceId: 1, status: 1, result: 'TIMEOUT' })
    assert.ok(system.controlError)
    ws.close()
    assert.equal(system.realtime, false)
    await new Promise(resolve => setTimeout(resolve, 3100))
    assert.equal(instances.length, 2)
    instances[1].onopen()
    assert.deepEqual(instances[1].sent, { type: 'auth', token: 'websocket-session-token' })
    instances[1].onmessage({ data: JSON.stringify({ type: 'authenticated' }) })
    await tick()
    assert.equal(system.sensors.temperature.value, 30, 'older REST snapshot must not replace newer sensor event')
    let expiredEvent
    const originalDispatch = globalThis.dispatchEvent
    globalThis.dispatchEvent = event => { expiredEvent = event.type }
    try {
      instances[1].close(4401)
      assert.equal(system.realtime, false)
      assert.equal(expiredEvent, 'auth-expired')
      let headers
      globalThis.fetch = async (url, options) => { headers = options.headers; return ok('OK') }
      await api('/api/auth/health')
      assert.equal(headers.Authorization, undefined)
    } finally {
      globalThis.dispatchEvent = originalDispatch
    }
  } finally { stopSystem(); setAccessToken('') }
})
