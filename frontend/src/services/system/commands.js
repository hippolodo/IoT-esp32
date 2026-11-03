import { api } from '../api.js'
import { system, applyThresholds, emitSystemEvent } from './state.js'
import { captureSystemSession, refreshDevices } from './connection.js'

// Nhận một đèn từ Dashboard, gửi trạng thái đảo 0/1 qua POST /api/devices/control.
// Khóa gửi trùng và lấy lại pending; chỉ ACK từ ESP32 mới xác nhận thiết lập đèn.
export async function toggleDevice(device) {
  if (system.sendingAll || system.sending[device.id] || device.pending) return
  const session = captureSystemSession()
  system.sending[device.id] = true
  system.controlError = ''
  let status
  if (device.status === 1) {
    status = 0
  } else {
    status = 1
  }
  try {
    // Gửi yêu cầu HTTP; không tự đổi device.status trước khi ESP32 xác nhận.
    await api('/api/devices/control', {
      method: 'POST',
      body: JSON.stringify({ deviceId: device.id, status }),
      signal: session.signal,
    })
    if (!session.isCurrent()) return
    await refreshDevices()
    if (!session.isCurrent()) return
    emitSystemEvent({ topic: '/topic/device-status', data: { deviceId: device.id } })
  } catch (error) {
    if (session.isCurrent()) system.controlError = error.message
  } finally {
    if (session.isCurrent()) delete system.sending[device.id]
  }
}

// Gửi song song ON/OFF cho các đèn cần đổi; gom lỗi từng đèn, không giả định tất cả thành công.
export async function controlAllDevices(status) {
  const devices = system.devices.filter((device) => device.controllable)
  if (
    ![0, 1].includes(status) ||
    system.sendingAll ||
    !system.backendOnline ||
    !system.mqttConnected ||
    system.esp32Online !== true ||
    devices.some((device) => device.pending || system.sending[device.id])
  ) return

  const targets = devices.filter((device) => device.status !== status)
  if (!targets.length) return
  const session = captureSystemSession()
  system.sendingAll = true
  system.controlError = ''
  targets.forEach((device) => { system.sending[device.id] = true })
  try {
    const results = await Promise.allSettled(targets.map(async (device) => {
      await api('/api/devices/control', {
        method: 'POST',
        body: JSON.stringify({ deviceId: device.id, status }),
        signal: session.signal,
      })
    }))
    if (!session.isCurrent()) return
    const errors = []
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        errors.push(`${targets[index].name}: ${result.reason.message}`)
      }
    })
    if (errors.length) system.controlError = errors.join('; ')
    // Refresh pending/confirmed states; do not assume HTTP success means the LED changed.
    await refreshDevices()
    if (!session.isCurrent()) return
    emitSystemEvent({ topic: '/topic/device-status', data: {} })
  } catch (error) {
    if (session.isCurrent())
      system.controlError = [system.controlError, error.message].filter(Boolean).join('; ')
  } finally {
    if (session.isCurrent()) {
      targets.forEach((device) => { delete system.sending[device.id] })
      system.sendingAll = false
    }
  }
}

// Gửi bản nháp ba ngưỡng qua POST /api/thresholds và cập nhật trạng thái trả về.
// HTTP kết thúc chưa chắc ESP32 đã áp dụng; confirmed được cập nhật tiếp qua WebSocket/REST.
export async function saveThresholds(values) {
  const session = captureSystemSession()
  // values là bản sao draft của form; JSON.stringify tạo chuỗi JSON cho request body.
  const data = await api('/api/thresholds', {
    method: 'POST',
    body: JSON.stringify(values),
    signal: session.signal,
  })
  if (session.isCurrent()) applyThresholds(data)
}
