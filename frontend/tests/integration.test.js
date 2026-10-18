import test from 'node:test'
import assert from 'node:assert/strict'
import { api, websocketUrl } from '../src/services/api.js'
import { system, startSystem, stopSystem, toggleDevice } from '../src/services/system.js'

const tick = () => new Promise(resolve => setImmediate(resolve))
const ok = data => ({ ok: true, json: async () => ({ success: true, data }) })

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
  globalThis.WebSocket = class {
    constructor() { instances.push(this) }
    close() { this.onclose?.() }
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
    await tick()
    assert.equal(system.sensors.temperature.value, 30, 'older REST snapshot must not replace newer sensor event')
  } finally { stopSystem() }
})
