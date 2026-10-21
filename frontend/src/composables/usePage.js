import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../services/api'
import { onSystemEvent } from '../services/system'

const PAGE_REFRESH_MS = 10000
const EVENT_DEBOUNCE_MS = 250

export function usePage(path, query, eventTopic) {
  const rows = ref([]),
    currentPage = ref(1),
    itemsPerPage = ref(10)
  const total = ref(0),
    totalPages = ref(0),
    loading = ref(false),
    error = ref('')
  const visiblePages = computed(() => {
    const first = Math.max(1, Math.min(currentPage.value - 2, totalPages.value - 4))
    return Array.from({ length: Math.min(5, totalPages.value) }, (_, i) => first + i)
  })
  let controller,
    active = true,
    sequence = 0
  let unsubscribe, timer, poll
  async function load() {
    controller?.abort()
    const id = ++sequence
    controller = new AbortController()
    loading.value = true
    error.value = ''
    try {
      const result = await api(path, {
        query: { ...query(), page: currentPage.value - 1, size: itemsPerPage.value },
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
      })
      if (!active || id !== sequence) return
      if (result.totalPages > 0 && currentPage.value > result.totalPages) {
        currentPage.value = result.totalPages
        return load()
      }
      rows.value = result.content
      total.value = result.totalElements
      totalPages.value = result.totalPages
    } catch (err) {
      if (active && id === sequence && err.name !== 'AbortError') {
        error.value = err.message
        rows.value = []
        total.value = totalPages.value = 0
      }
    } finally {
      if (active && id === sequence) loading.value = false
    }
  }
  const handleSizeChange = () => {
    currentPage.value = 1
    load()
  }
  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages.value && page !== currentPage.value) {
      currentPage.value = page
      load()
    }
  }
  onMounted(() => {
    load()
    poll = setInterval(load, PAGE_REFRESH_MS)
    unsubscribe = onSystemEvent((event) => {
      if (event.topic === eventTopic) {
        clearTimeout(timer)
        timer = setTimeout(load, EVENT_DEBOUNCE_MS)
      }
    })
  })
  onUnmounted(() => {
    active = false
    controller?.abort()
    unsubscribe?.()
    clearTimeout(timer)
    clearInterval(poll)
  })
  return {
    rows,
    currentPage,
    itemsPerPage,
    total,
    totalPages,
    visiblePages,
    loading,
    error,
    load,
    handleSizeChange,
    goToPage,
    nextPage: () => goToPage(currentPage.value + 1),
    prevPage: () => goToPage(currentPage.value - 1),
  }
}
