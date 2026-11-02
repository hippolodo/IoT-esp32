import { reactive } from 'vue'

function createInitialState() {
  return {
    backendOnline: false,
    realtime: false,
    mqttConnected: false,
    esp32Online: null,
    devices: [],
    sensors: {},
    points: [],
    chartLoading: false,
    chartError: '',
    error: '',
    sensorError: '',
    controlError: '',
    sending: {},
    sendingAll: false,
    thresholds: {},
    thresholdConfirmed: {},
    alertCounts: {},
  }
}

export const system = reactive(createInitialState())
const listeners = new Set()

export function resetSystemState() {
  Object.assign(system, createInitialState())
}

export function onSystemEvent(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function emitSystemEvent(event) {
  listeners.forEach((listener) => listener(event))
}

export function applyThresholds(data) {
  system.thresholds = data.values
  system.thresholdConfirmed = data.confirmed
}
