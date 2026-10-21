import test from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer, nextTick } from 'vue'
import { useWindAlerts } from '../src/composables/useWindAlerts.js'
import { startSystem, stopSystem } from '../src/services/system.js'

const tick = () => new Promise(resolve => setImmediate(resolve))
const ok = data => ({ ok: true, json: async () => ({ success: true, data }) })

test('wind statistics load only on mount, new alerts, changed filters and pagination', async () => {
  const requests = [], intervals = [], sockets = []
  const originalInterval = globalThis.setInterval
  globalThis.setInterval = (callback, delay) => { intervals.push(delay); return originalInterval(callback, delay) }
  globalThis.window = { location: { origin: 'http://localhost:5173' } }
  globalThis.WebSocket = class {
    constructor() { sockets.push(this) }
    send() {}
    close() { this.onclose?.({ code: 1000 }) }
  }
  globalThis.fetch = async (url) => {
    if (url.startsWith('/api/alerts/wind')) {
      requests.push(url)
      if (url.includes('/summary')) return ok({ total: 0, days: [] })
      return ok({ content: [], totalElements: 40, totalPages: 4 })
    }
    if (url === '/api/system/status') return ok({ mqttConnected: false, esp32Online: false })
    return ok([])
  }
  const renderer = createRenderer({
    createComment: () => ({}), createElement: () => ({}), createText: () => ({}),
    insert() {}, remove() {}, setText() {}, setElementText() {}, patchProp() {},
    parentNode: () => null, nextSibling: () => null,
  })
  let state
  const app = renderer.createApp({ setup() { state = useWindAlerts(); return () => null } })
  let mounted = false
  try {
    startSystem()
    app.mount({})
    mounted = true
    await tick()
    assert.equal(requests.length, 2, 'one initial summary and one initial daily list')
    assert.deepEqual(intervals, [5000], 'only the existing system refresh timer; no statistics polling')
    const emit = (topic, data) => sockets[0].onmessage({ data: JSON.stringify({ topic, data }) })
    for (const windSpeed of [100, 350, 400, 200]) emit('/topic/sensors', { windSpeed })
    await tick()
    assert.equal(requests.length, 2, 'ordinary wind readings must not reload statistics')

    const initialDate = state.selectedDate.value
    emit('/topic/wind-alerts', { id: 1, speed: 350, recordedAt: `${initialDate} 12:00:00` })
    await tick()
    assert.equal(requests.length, 4, 'new alert refreshes matching month and day')
    state.nextPage()
    await tick()
    assert.equal(requests.length, 5)
    assert.match(requests.at(-1), /page=1/)

    state.selectedDate.value = `${state.month.value}-${initialDate.endsWith('-01') ? '02' : '01'}`
    await nextTick()
    await tick()
    assert.equal(requests.length, 6, 'changing day only loads its list')
    assert.match(requests.at(-1), /page=0/)

    state.month.value = state.month.value === '2026-09' ? '2026-08' : '2026-09'
    await nextTick()
    await tick()
    assert.equal(requests.length, 8, 'changing month loads its summary and first day once each')
    emit('/topic/wind-alerts', { id: 2, speed: 400, recordedAt: `${initialDate} 12:01:00` })
    await tick()
    assert.equal(requests.length, 8, 'alerts outside the selected month/day cause no requests')
    emit('/topic/wind-alerts', { id: 3, speed: 400, recordedAt: `${state.month.value}-02 12:01:00` })
    await tick()
    assert.equal(requests.length, 9, 'another day in selected month refreshes summary only')
    assert.match(requests.at(-1), /\/summary\?/)
    app.unmount()
    mounted = false
    emit('/topic/wind-alerts', { id: 4, speed: 400, recordedAt: `${state.month.value}-01 12:02:00` })
    await tick()
    assert.equal(requests.length, 9, 'unmounted screen must unsubscribe')
  } finally {
    if (mounted) app.unmount()
    stopSystem()
    globalThis.setInterval = originalInterval
  }
})
