import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import * as Vue from 'vue'
import { compile } from '@vue/compiler-dom'
import { parse } from '@vue/compiler-sfc'
import { renderToString } from '@vue/server-renderer'

test('Action History renders visible manual and alert filter options', async () => {
  const source = await readFile(new URL('../src/views/ActionHistory.vue', import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const { code } = compile(descriptor.template.content, { mode: 'function', prefixIdentifiers: true })
  const render = new Function('Vue', code)(Vue)
  const noop = () => {}
  const app = Vue.createSSRApp({
    render,
    components: { ConnectionStatus: { render: () => null }, CopyTimestamp: { render: () => null } },
    data: () => ({
      system: { devices: [{ id: 1, name: 'LED 1' }] },
      searchDevice: 'all', searchStatus: 'all', searchAction: 'all', searchTime: '',
      loading: false, error: '', timeSortDirection: 'desc',
      paginatedData: [
        { id: 'LOG-1', userId: 'AUTO', deviceName: 'LED 1', gpio: 'GPIO 2',
          isIconActive: true, action: 'ALERT', actionClass: '', execStatusTextClass: '',
          execStatusColor: '', execStatus: 'RECORDED', deviceStatusColor: '', deviceStatus: '2 alerts',
          timestamp: '2026-10-28 12:00:00', date: '2026-10-28', time: '12:00:00',
          isAlert: true, alertCount: 2, alertValue: 32.5, alertThreshold: 30, alertUnit: '°C', alertExcess: 2.5 },
        { id: 'LOG-2', userId: 'AUTO', deviceName: 'LED 2', gpio: 'GPIO 5',
          isIconActive: true, action: 'ALERT', actionClass: '', execStatusTextClass: '',
          execStatusColor: '', execStatus: 'RECORDED', deviceStatusColor: '', deviceStatus: '1 alert',
          timestamp: '2026-10-28 12:00:00', date: '2026-10-28', time: '12:00:00',
          isAlert: true, alertCount: 1, alertValue: null, alertThreshold: null },
      ],
      currentPage: 1, total: 0, totalPages: 0, itemsPerPage: 10, visiblePages: [],
      resetDeviceFilters: noop, handleSearch: noop, handleReset: noop,
      toggleTimeSort: noop, handleSizeChange: noop, prevPage: noop, nextPage: noop, goToPage: noop,
    }),
  })
  const html = await renderToString(app)
  const selects = [...html.matchAll(/<select\b[^>]*>([\s\S]*?)<\/select>/g)].map(match => match[1])
  assert.equal(selects.length, 4)
  for (const value of ['SUCCESS', 'FAILED', 'PENDING', 'RECORDED'])
    assert.match(selects[1], new RegExp(`<option value="${value}">`))
  for (const value of ['ON', 'OFF', 'ALERT'])
    assert.match(selects[2], new RegExp(`<option value="${value}">`))
  assert.equal(selects[1].includes('<template'), false)
  assert.equal(selects[2].includes('<template'), false)
  assert.match(html.replace(/\s+/g, ' '), /32.5 °C &gt; 30 °C/)
  assert.match(html, /Chưa lưu giá trị lúc vượt/)
})
