import test from 'node:test'
import assert from 'node:assert/strict'
import { api, getAccessToken, setAccessToken } from '../src/services/api.js'
import {
  system, startSystem, stopSystem, resetSystemState, refreshDevices,
  toggleDevice, controlAllDevices, saveThresholds, onSystemEvent,
} from '../src/services/system.js'

const tick = () => new Promise(resolve => setImmediate(resolve))
const ok = data => ({ ok: true, json: async () => ({ success: true, data }) })
const failed = { ok: false, status: 503, json: async () => ({ message: 'Old session failed' }) }

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

function setup(t) {
  stopSystem()
  resetSystemState()
  const sockets = []
  globalThis.window = { location: { origin: 'http://localhost:5173' } }
  globalThis.WebSocket = class {
    constructor() { sockets.push(this) }
    send() {}
    close() { this.onclose?.({ code: 1000 }) }
  }
  const snapshot = async url => {
    if (url === '/api/system/status') return ok({ mqttConnected: true, esp32Online: true })
    if (url === '/api/devices') return ok([{ id: 1, name: 'Current lamp', status: 0, controllable: true }])
    if (url === '/api/thresholds') return ok({ values: { temperature: 35 }, confirmed: { temperature: true } })
    if (url === '/api/alert-counts') return ok({ 1: 7 })
    if (url === '/api/sensors/latest' || url.startsWith('/api/sensors/chart')) return ok([])
    throw new Error(`Unexpected request: ${url}`)
  }
  globalThis.fetch = snapshot
  t.after(() => {
    stopSystem()
    resetSystemState()
    setAccessToken('')
  })
  return { snapshot, sockets }
}

test('periodic checks only request connection status while WebSocket updates live data', async t => {
  const { snapshot, sockets } = setup(t)
  let poll
  t.mock.method(globalThis, 'setInterval', (callback, milliseconds) => {
    assert.equal(milliseconds, 5000)
    poll = callback
    return 0
  })
  const requests = []
  globalThis.fetch = async (url, options) => {
    requests.push(url)
    return snapshot(url, options)
  }
  startSystem()
  await tick()
  requests.length = 0
  poll()
  await tick()
  assert.deepEqual(requests, ['/api/system/status'])

  const message = (topic, data) => sockets[0].onmessage({ data: JSON.stringify({ topic, data }) })
  requests.length = 0
  message('/topic/alert-counts', { 1: 9 })
  message('/topic/thresholds', { values: { temperature: 30 }, confirmed: { temperature: true } })
  message('/topic/sensors', { temperature: 33 })
  assert.equal(system.alertCounts[1], 9)
  assert.equal(system.thresholds.temperature, 30)
  assert.equal(system.sensors.temperature.value, 33)
  assert.deepEqual(requests, [])
  message('/topic/device-status', { deviceId: 1, status: 1, result: 'ON' })
  assert.equal(system.devices[0].status, 1)
  await tick()
  assert.deepEqual(requests, ['/api/devices'])
})

test('WebSocket reconnection reloads snapshots missed during disconnection', async t => {
  const { snapshot, sockets } = setup(t)
  let reconnect
  t.mock.method(globalThis, 'setTimeout', (callback, milliseconds) => {
    assert.equal(milliseconds, 3000)
    reconnect = callback
    return 0
  })
  const requests = []
  let total = 7
  globalThis.fetch = async (url, options) => {
    requests.push(url)
    return url === '/api/alert-counts' ? ok({ 1: total }) : snapshot(url, options)
  }
  startSystem()
  await tick()
  sockets[0].onmessage({ data: JSON.stringify({ type: 'authenticated' }) })
  await tick()
  sockets[0].onclose({ code: 1006 })
  total = 12
  requests.length = 0
  reconnect()
  sockets[1].onmessage({ data: JSON.stringify({ type: 'authenticated' }) })
  await tick()
  assert.equal(system.realtime, true)
  assert.equal(system.alertCounts[1], 12)
  for (const url of ['/api/devices', '/api/sensors/latest', '/api/thresholds', '/api/alert-counts'])
    assert.ok(requests.includes(url), `missing reconnect snapshot: ${url}`)
})

for (const response of ['success', 'failure']) {
  test(`late REST ${response} cannot overwrite a restarted session`, async t => {
    const { snapshot, sockets } = setup(t)
    const pending = deferred()
    const signals = []
    globalThis.fetch = async (url, options) => {
      if (url.startsWith('/api/sensors/chart')) return snapshot(url)
      signals.push(options.signal)
      await pending.promise
      return response === 'failure' ? failed : ok([])
    }
    startSystem()
    await tick()
    const oldSocket = sockets[0]
    stopSystem()
    resetSystemState()
    assert.equal(signals.length, 5)
    assert.ok(signals.every(signal => signal.aborted))

    globalThis.fetch = snapshot
    startSystem()
    await tick()
    const expected = JSON.parse(JSON.stringify(system))
    pending.resolve()
    oldSocket.onmessage({ data: JSON.stringify({ topic: '/topic/alert-counts', data: { 1: 999 } }) })
    oldSocket.onclose({ code: 4401 })
    await tick()
    assert.deepEqual(JSON.parse(JSON.stringify(system)), expected)
  })
}

test('late device response cannot repopulate state after logout', async t => {
  setup(t)
  const pending = deferred()
  let signal
  globalThis.fetch = async (url, options) => {
    signal = options.signal
    return pending.promise
  }
  const request = refreshDevices()
  const settled = Promise.allSettled([request])
  stopSystem()
  resetSystemState()
  pending.resolve(ok([{ id: 99, name: 'Previous session' }]))
  await settled
  assert.equal(signal.aborted, true)
  assert.deepEqual(system.devices, [])
})

for (const command of ['toggle', 'bulk', 'thresholds']) {
  test(`late ${command} response cannot update or clear the next session's state`, async t => {
    const { snapshot } = setup(t)
    startSystem()
    await tick()
    const pending = deferred()
    let signal
    globalThis.fetch = async (url, options) => {
      if (options.method !== 'POST') return snapshot(url)
      signal = options.signal
      return pending.promise
    }
    let events = 0
    const unsubscribe = onSystemEvent(() => { events++ })
    t.after(unsubscribe)
    const request = command === 'toggle' ? toggleDevice(system.devices[0])
      : command === 'bulk' ? controlAllDevices(1)
        : saveThresholds({ temperature: 20, humidity: 60, light: 1000 })
    const settled = Promise.allSettled([request])
    stopSystem()
    resetSystemState()
    globalThis.fetch = snapshot
    startSystem()
    await tick()
    // An old command's finally block must not clear a new command's busy flags.
    system.sending = { 1: true }
    system.sendingAll = true
    const expected = JSON.parse(JSON.stringify(system))
    pending.resolve(command === 'thresholds'
      ? ok({ values: { temperature: 20 }, confirmed: {} }) : failed)
    await settled
    assert.equal(signal.aborted, true)
    assert.equal(events, 0)
    assert.deepEqual(JSON.parse(JSON.stringify(system)), expected)
  })
}

test('an old unauthorized response cannot expire a new access token', async t => {
  setup(t)
  const pending = deferred()
  globalThis.fetch = async () => pending.promise
  setAccessToken('old-session')
  const request = api('/api/devices')
  const rejected = assert.rejects(request, /Old session expired/)
  setAccessToken('new-session')
  pending.resolve({ ok: false, status: 401, json: async () => ({ message: 'Old session expired' }) })
  await rejected
  assert.equal(getAccessToken(), 'new-session')
})

test('API keeps its timeout when the caller supplies a cancellation signal', async t => {
  setup(t)
  const caller = new AbortController()
  const timeout = new AbortController()
  const originalTimeout = AbortSignal.timeout
  AbortSignal.timeout = milliseconds => {
    assert.equal(milliseconds, 10000)
    return timeout.signal
  }
  t.after(() => { AbortSignal.timeout = originalTimeout })
  globalThis.fetch = async (url, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(signal.reason), { once: true })
  })
  const request = api('/api/devices', { signal: caller.signal })
  const rejected = assert.rejects(request, /Backend phản hồi quá chậm/)
  timeout.abort(new DOMException('Request timed out', 'TimeoutError'))
  await rejected
  assert.equal(caller.signal.aborted, false)
})
