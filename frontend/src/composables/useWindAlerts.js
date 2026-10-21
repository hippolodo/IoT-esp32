import { onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../services/api.js'
import { onSystemEvent } from '../services/system.js'
import { usePage } from './usePage.js'

export function useWindAlerts() {
  const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' })
  const month = ref(today.slice(0, 7))
  const selectedDate = ref(today)
  const days = ref([])
  const totalAlerts = ref(0)
  const summaryError = ref('')
  const summaryLoading = ref(false)
  let controller, unsubscribe
  let active = true
  const page = usePage('/api/alerts/wind', () => ({ date: selectedDate.value }), null, { pollIntervalMs: 0 })

  async function loadSummary() {
    controller?.abort()
    if (!/^\d{4}-\d{2}$/.test(month.value)) {
      summaryError.value = 'Vui lòng chọn tháng hợp lệ.'
      summaryLoading.value = false
      return
    }
    const request = new AbortController()
    controller = request
    summaryLoading.value = true
    summaryError.value = ''
    try {
      const result = await api('/api/alerts/wind/summary', {
        query: { month: month.value },
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(10000)]),
      })
      if (!active || controller !== request) return
      days.value = result.days
      totalAlerts.value = result.total
    } catch (err) {
      if (active && controller === request && err.name !== 'AbortError') summaryError.value = err.message
    } finally {
      if (active && controller === request) summaryLoading.value = false
    }
  }

  watch(month, () => {
    days.value = []
    totalAlerts.value = 0
    if (/^\d{4}-\d{2}$/.test(month.value)) selectedDate.value = `${month.value}-01`
    loadSummary()
  })
  watch(selectedDate, () => { page.currentPage.value = 1; page.load() })

  onMounted(() => {
    loadSummary()
    unsubscribe = onSystemEvent((event) => {
      if (event.topic !== '/topic/wind-alerts') return
      const date = event.data.recordedAt?.slice(0, 10)
      if (!date) return
      if (date.slice(0, 7) === month.value) loadSummary()
      if (date === selectedDate.value) page.load()
    })
  })
  onUnmounted(() => {
    active = false
    controller?.abort()
    unsubscribe?.()
  })

  return { month, selectedDate, days, totalAlerts, summaryError, summaryLoading, ...page }
}
