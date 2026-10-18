<template>
  <div class="flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold"
       :class="system.backendOnline && system.mqttConnected && system.esp32Online ? 'bg-green-50 text-green-700 border-green-200' : 'bg-amber-50 text-amber-700 border-amber-200'" role="status">
    <span class="h-2 w-2 rounded-full bg-current"></span>{{ label }}
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { system } from '../services/system'
const label = computed(() => {
  if (!system.backendOnline) return 'Backend chưa kết nối'
  if (!system.mqttConnected) return 'MQTT chưa kết nối'
  if (system.esp32Online === false) return 'ESP32 mất kết nối'
  if (system.esp32Online == null) return 'Đang chờ ESP32'
  return system.realtime ? 'ESP32 đã kết nối' : 'ESP32 online · Đang nối lại realtime'
})
</script>
