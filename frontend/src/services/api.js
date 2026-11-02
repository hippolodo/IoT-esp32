const base = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')
const REQUEST_TIMEOUT_MS = 10000
let accessToken = globalThis.sessionStorage?.getItem('accessToken') || ''

export function setAccessToken(token) {
  accessToken = token || ''
  if (accessToken) globalThis.sessionStorage?.setItem('accessToken', accessToken)
  else globalThis.sessionStorage?.removeItem('accessToken')
}

export function getAccessToken() {
  return accessToken
}

export function expireSession() {
  setAccessToken('')
  globalThis.dispatchEvent?.(new Event('auth-expired'))
}

export async function api(path, { query, ...options } = {}) {
  const requestToken = accessToken
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout
  const params = new URLSearchParams()
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value)
  })
  try {
    const response = await fetch(`${base}${path}${params.size ? `?${params}` : ''}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(requestToken ? { Authorization: `Bearer ${requestToken}` } : {}),
        ...options.headers,
      },
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

export function websocketUrl() {
  const url = new URL(`${base}/ws`, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}
