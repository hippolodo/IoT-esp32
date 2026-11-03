import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import * as Vue from 'vue'
import { parse } from '@vue/compiler-sfc'
import { parse as parseJavaScript } from '@babel/parser'

// Chạy phần script thực của màn hình với API/lifecycle giả lập, không cần trình duyệt.
async function readView(name, exposed, overrides = {}) {
  const source = await readFile(new URL(`../src/${name}`, import.meta.url), 'utf8')
  const script = parse(source).descriptor.scriptSetup.content
  const imports = parseJavaScript(script, { sourceType: 'module' }).program.body
    .filter(node => node.type === 'ImportDeclaration')
  let body = script
  const bindings = {}
  for (const node of imports) {
    for (const specifier of node.specifiers) {
      const name = specifier.local.name
      if (Object.hasOwn(overrides, name)) {
        bindings[name] = overrides[name]
      } else if (name === 'onMounted' || name === 'onUnmounted') {
        bindings[name] = () => {}
      } else if (node.source.value === 'vue') {
        bindings[name] = Vue[specifier.imported.name]
      } else if (name === 'ChartJS') {
        bindings[name] = { register() {} }
      } else {
        bindings[name] = () => {}
      }
    }
  }
  for (const node of [...imports].reverse()) body = body.slice(0, node.start) + body.slice(node.end)
  const run = new Function(...Object.keys(bindings), `${body}\nreturn { ${exposed.join(', ')} }`)
  return run(...Object.values(bindings))
}

test('registration rules apply only while the registration form is active', async () => {
  const view = await readView('App.vue', ['isRegistering', 'usernameRules', 'passwordRules'])
  assert.deepEqual(view.usernameRules.value, {})
  assert.deepEqual(view.passwordRules.value, { autocomplete: 'current-password' })
  view.isRegistering.value = true
  assert.equal(view.usernameRules.value.minlength, 3)
  assert.equal(view.usernameRules.value.maxlength, 50)
  assert.equal(view.usernameRules.value.pattern, '[A-Za-z0-9_.-]{3,50}')
  assert.deepEqual(view.passwordRules.value, { autocomplete: 'new-password', minlength: 8, maxlength: 128 })
  view.isRegistering.value = false
  assert.deepEqual(view.usernameRules.value, {})
})

test('history keeps manual and alert results, colors and sorting after expanding conditions', async () => {
  const rows = Vue.ref([
    { id: 1, action: 'ON', status: 'SUCCESS', userId: 4 },
    { id: 2, action: 'OFF', status: 'SUCCESS', userId: 4 },
    { id: 3, action: 'ON', status: 'PENDING' },
    { id: 4, action: 'OFF', status: 'FAILED' },
    { id: 5, action: 'ALERT', status: 'RECORDED', alertCount: 2, alertTotal: 12, alertValue: 35, alertThreshold: 30 },
  ].map(row => ({ ...row, deviceId: 1, deviceName: 'Đèn 1', timestamp: '2026-11-03 10:00:00' })))
  const currentPage = Vue.ref(1)
  let query
  const view = await readView('views/ActionHistory.vue', [
    'paginatedData', 'applied', 'timeSortAria', 'timeSortTitle', 'timeSortIcon', 'toggleTimeSort',
  ], {
    system: { devices: [{ id: 1, controlPin: 2, sensorKey: 'temperature' }] },
    usePage(path, getQuery) {
      query = getQuery
      return { rows, currentPage, load() {} }
    },
  })
  assert.deepEqual(view.paginatedData.value.map(row => [
    row.action, row.execStatusColor, row.deviceStatus, row.deviceStatusColor,
  ]), [
    ['BẬT (ON)', 'bg-emerald-500', 'BẬT', 'bg-emerald-500'],
    ['TẮT (OFF)', 'bg-emerald-500', 'TẮT', 'bg-emerald-500'],
    ['BẬT (ON)', 'bg-amber-500', 'Chưa xác nhận', 'bg-gray-300'],
    ['TẮT (OFF)', 'bg-red-500', 'Chưa xác nhận', 'bg-gray-300'],
    ['CẢNH BÁO', 'bg-amber-500', '+2 lần · Tổng 12', 'bg-red-500'],
  ])
  const alert = view.paginatedData.value[4]
  assert.equal(alert.userId, 'Tự động')
  assert.equal(alert.alertExcess, 5)
  assert.equal(alert.gpio, 'GPIO 2')
  assert.equal(view.timeSortAria.value, 'descending')
  view.toggleTimeSort()
  assert.equal(view.timeSortAria.value, 'ascending')
  assert.equal(view.timeSortIcon.value, 'fa-arrow-up')
  assert.equal(query().sort, 'asc')
  view.applied.value = { device: 1, status: 'RECORDED', action: 'ALERT', time: '' }
  assert.equal(query().deviceId, 1)
  assert.equal(query().action, 'ALERT')
})

test('sensor filters keep time and numeric searches separate', async () => {
  const rows = Vue.ref([
    { id: 1, sensorName: 'LDR', sensorType: 'LIGHT', value: 2500, unit: 'old unit', recordedAt: '2026-11-03 10:00:00' },
  ])
  let query
  const view = await readView('views/DataSensors.vue', ['applied', 'paginatedData'], {
    usePage(path, getQuery) {
      query = getQuery
      return { rows }
    },
  })
  assert.equal(view.paginatedData.value[0].value, '2500 ADC')
  view.applied.value = { type: 'TIME', value: '2026-11-03' }
  assert.deepEqual(query(), { startTime: '2026-11-03', endTime: '2026-11-03' })
  view.applied.value = { type: 'TEMPERATURE', value: '35' }
  assert.deepEqual(query(), { sensorType: 'TEMPERATURE', value: '35' })
})
