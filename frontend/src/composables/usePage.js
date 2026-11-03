import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../services/api.js'
import { onSystemEvent } from '../services/system.js'

const PAGE_REFRESH_MS = 10000
const EVENT_DEBOUNCE_MS = 250

// Logic dùng chung cho bảng số đo/lịch sử: gọi API có bộ lọc, phân trang và tự làm mới.
// Trả các ref/hàm để màn hình hiển thị; query() cung cấp bộ lọc đã áp dụng.
export function usePage(path, query, eventTopic, { pollIntervalMs = PAGE_REFRESH_MS } = {}) {
  let eventTopics
  if (Array.isArray(eventTopic)) {
    eventTopics = eventTopic
  } else {
    eventTopics = [eventTopic]
  }
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
  // Hủy request cũ, lấy trang hiện tại và lưu content/tổng số trang; bỏ kết quả khi đã unmount.
  async function load() {
    controller?.abort()
    const id = ++sequence
    controller = new AbortController()
    loading.value = true
    error.value = ''
    try {
      const result = await api(path, {
        query: { ...query(), page: currentPage.value - 1, size: itemsPerPage.value },
        signal: controller.signal,
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
  // Đổi số dòng mỗi trang thì trở về trang 1 để tránh trỏ tới trang không còn tồn tại.
  const handleSizeChange = () => {
    currentPage.value = 1
    load()
  }
  // Chỉ chuyển tới trang hợp lệ khác trang hiện tại rồi tải dữ liệu của trang đó.
  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages.value && page !== currentPage.value) {
      currentPage.value = page
      load()
    }
  }
  // Khi mở màn hình: tải ngay, bật polling và nghe sự kiện với debounce để tránh gọi API dồn dập.
  onMounted(() => {
    load()
    if (pollIntervalMs > 0) poll = setInterval(load, pollIntervalMs)
    if (eventTopic) unsubscribe = onSystemEvent((event) => {
      if (eventTopics.includes(event.topic)) {
        clearTimeout(timer)
        timer = setTimeout(load, EVENT_DEBOUNCE_MS)
      }
    })
  })
  // Khi rời màn hình: hủy request, hủy đăng ký sự kiện và dừng toàn bộ timer của bảng.
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
