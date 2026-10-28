<template>
  <div class="animate-fade-in text-gray-800">
    <div class="flex justify-between items-start mb-8">
      <div>
        <h2 class="text-2xl font-bold">Dashboard Tổng Quan</h2>
        <p class="text-sm text-gray-500 mt-1">
          Cập nhật dữ liệu cảm biến và điều khiển thiết bị theo thời gian thực
        </p>
      </div>
      <ConnectionStatus />
    </div>

    <p v-if="system.sensorError" role="alert" class="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
      {{ system.sensorError }} — nhiệt độ/độ ẩm đang hiển thị giá trị hợp lệ gần nhất.
    </p>
    <p v-if="system.controlError" role="alert" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
      {{ system.controlError }}
    </p>
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400">TỐC ĐỘ GIÓ</span>
          <i class="fa-solid fa-wind text-cyan-600" aria-hidden="true"></i>
        </div>
        <p><span class="text-4xl font-bold">{{ system.sensors.windSpeed?.value ?? '—' }}</span> m/s</p>
        <p class="mt-2 text-xs" :class="system.sensors.windSpeed?.value > 300 ? 'text-red-600' : 'text-gray-500'">
          {{ system.sensors.windSpeed?.value > 300 ? 'Vượt 300 m/s · LED cảnh báo nhấp nháy' : 'LED tự cảnh báo khi vượt 300 m/s' }}
        </p>
        <p v-if="system.esp32Online !== true" class="mt-1 text-xs text-amber-700">Giá trị ghi nhận gần nhất</p>
      </div>
      <div
        class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400 tracking-wider">NHIỆT ĐỘ</span>
          <div class="w-8 h-8 rounded-full bg-red-50 text-red-500 flex items-center justify-center">
            <i class="fa-solid fa-temperature-half"></i>
          </div>
        </div>
        <div class="flex items-baseline space-x-1">
          <span class="text-4xl font-bold">{{ system.sensors.temperature?.value ?? '—' }}</span>
          <span class="text-xl text-gray-500">°C</span>
        </div>
      </div>

      <div
        class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400 tracking-wider uppercase">Độ Ẩm</span>
          <div class="w-8 h-8 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center">
            <i class="fa-solid fa-droplet"></i>
          </div>
        </div>
        <div class="flex items-baseline space-x-1">
          <span class="text-4xl font-bold">{{ system.sensors.humidity?.value ?? '—' }}</span>
          <span class="text-xl text-gray-500">%</span>
        </div>
      </div>
      <div
        class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400 tracking-wider uppercase">Ánh Sáng</span>
          <div class="w-8 h-8 rounded-full bg-amber-50 text-amber-500 flex items-center justify-center">
            <i class="fa-regular fa-sun"></i>
          </div>
        </div>
        <div class="flex items-baseline space-x-1">
          <span class="text-4xl font-bold">{{ system.sensors.light?.value ?? '—' }}</span>
          <span class="text-xl text-gray-500">ADC</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div class="flex items-center mb-6">
          <i class="fa-solid fa-chart-line text-blue-500 mr-2 text-lg"></i>
          <h3 class="text-lg font-bold">Biểu Đồ Cảm Biến · 30 điểm gần nhất</h3>
        </div>

        <p v-if="system.chartLoading" role="status" class="mb-3 text-sm text-gray-500">Đang tải lịch sử biểu đồ…</p>
        <p v-if="system.chartError" role="alert" class="mb-3 text-sm text-red-600">Không tải được lịch sử: {{ system.chartError }}</p>
        <p v-if="!system.chartLoading && !system.chartError && !system.points.length" class="mb-3 text-sm text-gray-500">Chưa có dữ liệu cảm biến trong database.</p>
        <div class="h-96 w-full relative">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <div class="lg:col-span-1 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div class="flex items-center mb-6">
          <i class="fa-regular fa-lightbulb text-amber-500 mr-2 text-lg"></i>
          <h3 class="text-lg font-bold">Điều Khiển Đèn</h3>
        </div>

        <p v-if="!lamps.length" class="text-sm text-gray-500">Chưa có thiết bị.</p>
        <div v-if="lamps.length" class="grid grid-cols-2 gap-3 mb-4" :aria-busy="system.sendingAll">
          <button
            type="button"
            @click="controlAllDevices(1)"
            :disabled="allControlsDisabled || controllableLamps.every((lamp) => lamp.isOn)"
            class="rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Bật tất cả
          </button>
          <button
            type="button"
            @click="controlAllDevices(0)"
            :disabled="allControlsDisabled || controllableLamps.every((lamp) => lamp.status === 0)"
            class="rounded-xl bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Tắt tất cả
          </button>
        </div>
        <p v-if="system.sendingAll" role="status" class="mb-3 text-xs text-blue-600">
          Đang gửi lệnh đến các đèn…
        </p>
        <div class="space-y-4">
          <div
            v-for="lamp in lamps"
            :key="lamp.id"
            class="flex items-center justify-between p-4 rounded-xl border border-gray-50 bg-gray-50/50 hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-center space-x-3">
              <div
                :class="[
                  'w-10 h-10 rounded-full flex items-center justify-center transition-colors',
                  lamp.isOn ? 'bg-blue-100 text-blue-600' : 'bg-red-50 text-red-600 border border-red-200',
                ]"
              >
                <i class="fa-regular fa-lightbulb text-lg"></i>
              </div>
              <div>
                <p class="text-sm font-bold">{{ lamp.name }}</p>
                <p class="text-xs text-gray-500">{{ lamp.gpio }}</p>
                <p class="text-xs text-amber-700" v-if="!lamp.controllable">Chưa cấu hình điều khiển</p>
                <p class="text-xs text-blue-600" v-else-if="lamp.pending || system.sending[lamp.id]">
                  Đang chờ ESP32 xác nhận…
                </p>
              </div>
            </div>

            <button
              @click="toggleDevice(lamp)"
              :disabled="
                !system.backendOnline ||
                !system.mqttConnected ||
                system.esp32Online !== true ||
                system.sendingAll ||
                !lamp.controllable ||
                lamp.pending ||
                system.sending[lamp.id]
              "
              :aria-checked="lamp.isOn"
              role="switch"
              :aria-label="lamp.name"
              :class="[
                'disabled:opacity-40 disabled:cursor-not-allowed relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                lamp.isOn ? 'bg-blue-600' : 'bg-gray-200',
              ]"
            >
              <span class="sr-only">Toggle {{ lamp.name }}</span>
              <span
                :class="[
                  'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-500 ease-in-out',
                  lamp.isOn ? 'translate-x-5' : 'translate-x-0',
                ]"
              ></span>
            </button>
          </div>
          <div class="flex items-center justify-between gap-3 p-4 rounded-xl border border-gray-100 bg-gray-50/50">
            <div class="flex items-center space-x-3">
              <div :class="[
                'w-10 h-10 shrink-0 rounded-full flex items-center justify-center',
                warningLamp.active && warningLamp.online ? 'wind-warning-blink' : 'bg-gray-100 text-gray-400',
              ]">
                <i class="fa-regular fa-lightbulb text-lg" aria-hidden="true"></i>
              </div>
              <div>
                <p class="text-sm font-bold">{{ warningLamp.name }}</p>
                <p class="text-xs text-gray-500">GPIO{{ warningLamp.gpio }} · Tự động khi gió &gt;300 m/s</p>
                <p role="status" :class="['mt-1 text-xs', warningLamp.active && warningLamp.online ? 'text-red-600' : 'text-gray-500']">
                  {{ warningLamp.label }}
                </p>
              </div>
            </div>
            <span class="shrink-0 rounded-full bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">Tự động</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'vue-chartjs'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import { system, toggleDevice, controlAllDevices } from '../services/system'
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)
const lamps = computed(() =>
  system.devices.filter((row) => row.type !== 'WIND_WARNING').map((row) => ({
    ...row,
    isOn: row.status === 1,
    gpio: row.controlPin != null ? `GPIO ${row.controlPin}` : `GPIO ${row.pinGpio ?? '—'}`,
  })),
)
const controllableLamps = computed(() => lamps.value.filter((lamp) => lamp.controllable))
const warningLamp = computed(() => {
  const device = system.devices.find((row) => row.type === 'WIND_WARNING')
  const speed = system.sensors.windSpeed?.value
  const known = typeof speed === 'number' && Number.isFinite(speed)
  const active = known && speed > 300
  const online = system.backendOnline && system.mqttConnected && system.esp32Online === true
  return {
    name: device?.name || 'Đèn cảnh báo',
    gpio: device?.pinGpio ?? 18,
    active,
    online,
    label: !known ? 'Chưa có dữ liệu tốc độ gió'
      : !online ? `Ghi nhận cuối: ${active ? 'Cảnh báo' : 'Không cảnh báo'} · Mất kết nối`
      : active ? 'Đang cảnh báo · Nhấp nháy' : 'Bình thường · Đèn tắt',
  }
})
const allControlsDisabled = computed(() =>
  !system.backendOnline ||
  !system.mqttConnected ||
  system.esp32Online !== true ||
  system.sendingAll ||
  !controllableLamps.value.length ||
  controllableLamps.value.some((lamp) => lamp.pending || system.sending[lamp.id]),
)
const latestTime = computed(
  () =>
    Object.values(system.sensors)
      .map((row) => row.time)
      .sort()
      .at(-1) || 'Chưa có dữ liệu',
)
const chartData = computed(() => ({
  labels: system.points.map((row) => row.time.slice(11)),
  datasets: [
    { key: 'temperature', label: 'Nhiệt độ (°C)', borderColor: '#ef4444', yAxisID: 'y' },
    { key: 'humidity', label: 'Độ ẩm (%)', borderColor: '#3b82f6', yAxisID: 'y' },
    { key: 'light', label: 'Ánh sáng (ADC)', borderColor: '#f59e0b', yAxisID: 'y2' },
    { key: 'windSpeed', label: 'Tốc độ gió (m/s)', borderColor: '#10b981', yAxisID: 'y2' },
  ].map(({ key, ...style }) => ({
    ...style,
    data: system.points.map((row) => row[key] ?? null),
    tension: 0.4,
  })),
}))
const chartOptions = ref({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      position: 'top',
      labels: {
        usePointStyle: true,
        boxWidth: 8,
        font: { family: 'Inter, sans-serif', size: 12 },
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
    },
    y: {
      type: 'linear',
      display: true,
      position: 'left',
      min: 10,
      max: 80,
      ticks: { stepSize: 20 },
      title: { display: true, text: 'Nhiệt độ (°C) / Độ ẩm (%)' },
      grid: { borderDash: [4, 4] },
    },
    y2: {
      type: 'linear',
      display: true,
      position: 'right',
      min: 0,
      max: 5000,
      title: { display: true, text: 'Ánh sáng (ADC) / Tốc độ gió (m/s)' },
      grid: { display: false },
    },
  },
})
</script>

<style scoped>
.wind-warning-blink {
  animation: wind-warning-blink 1000ms steps(1, end) infinite;
}

@keyframes wind-warning-blink {
  0%, 100% {
    background-color: #fee2e2;
    color: #dc2626;
  }
  50% {
    background-color: #f3f4f6;
    color: #9ca3af;
  }
}
</style>
