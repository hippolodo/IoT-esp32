const base = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')
const REQUEST_TIMEOUT_MS = 10000
let accessToken = globalThis.sessionStorage?.getItem('accessToken') || ''

// Lưu token trong bộ nhớ và sessionStorage; token rỗng thì xóa phiên phía trình duyệt.
export function setAccessToken(token) {
  accessToken = token || ''
  if (accessToken) globalThis.sessionStorage?.setItem('accessToken', accessToken)
  else globalThis.sessionStorage?.removeItem('accessToken')
}

// Lấy token hiện tại để gửi bản tin xác thực khi mở WebSocket.
export function getAccessToken() {
  return accessToken
}

// Xóa token và báo App.vue quay về màn đăng nhập khi phiên hết hạn.
export function expireSession() {
  setAccessToken('')
  globalThis.dispatchEvent?.(new Event('auth-expired'))
}

// Hàm HTTP dùng chung: ghép URL/query, thêm Bearer token và timeout 10 giây.
// Trả body.data nếu thành công; lỗi HTTP/nghiệp vụ được ném về catch của nơi gọi.
export async function api(path, { query, ...options } = {}) {
  const requestToken = accessToken
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  let signal
  if (options.signal) {
    signal = AbortSignal.any([options.signal, timeout])
  } else {
    signal = timeout
  }
  const params = new URLSearchParams()
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value)
  })
  let url = `${base}${path}`
  if (params.size) {
    url += `?${params}`
  }
  const headers = { 'Content-Type': 'application/json' }
  if (requestToken) {
    headers.Authorization = `Bearer ${requestToken}`
  }
  Object.assign(headers, options.headers)
  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal,
    })
    const body = await response.json().catch(() => null)
    signal.throwIfAborted()
    if (response.status === 401 && requestToken && requestToken === accessToken) {
      expireSession()
    }
    if (!response.ok || !body?.success) throw new Error(body?.message || `API trả lỗi ${response.status}`)
    return body.data
  } catch (error) {
    if (error.name === 'TimeoutError') throw new Error('Backend phản hồi quá chậm. Vui lòng thử lại.')
    if (error instanceof TypeError)
      throw new Error('Không kết nối được backend. Kiểm tra FastAPI ở cổng 8088.')
    throw error
  }
}

// Tạo URL /ws theo backend đã cấu hình; trang HTTPS dùng wss, còn HTTP dùng ws.
export function websocketUrl() {
  const url = new URL(`${base}/ws`, window.location.origin)
  if (url.protocol === 'https:') {
    url.protocol = 'wss:'
  } else {
    url.protocol = 'ws:'
  }
  return url.toString()
}
