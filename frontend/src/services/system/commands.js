import { api } from '../api.js'
import { system, applyThresholds, emitSystemEvent } from './state.js'
import { captureSystemSession, refreshDevices } from './connection.js'

export async function toggleDevice(device) {
  if (system.sendingAll || system.sending[device.id] || device.pending) return
  const session = captureSystemSession()
  system.sending[device.id] = true
  system.controlError = ''
  try {
    await api('/api/devices/control', {
      method: 'POST',
      body: JSON.stringify({ deviceId: device.id, status: device.status === 1 ? 0 : 1 }),
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
    const errors = results.flatMap((result, index) =>
      result.status === 'rejected'
        ? [`${targets[index].name}: ${result.reason.message}`]
        : [],
    )
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

export async function saveThresholds(values) {
  const session = captureSystemSession()
  const data = await api('/api/thresholds', {
    method: 'POST',
    body: JSON.stringify(values),
    signal: session.signal,
  })
  if (session.isCurrent()) applyThresholds(data)
}
