// Public entry point: components keep importing from services/system.
export { system, onSystemEvent, resetSystemState } from './system/state.js'
export { startSystem, stopSystem, refreshSystem, refreshDevices, refreshChartHistory } from './system/connection.js'
export { toggleDevice, controlAllDevices, saveThresholds } from './system/commands.js'
