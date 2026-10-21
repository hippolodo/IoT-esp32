<template>
  <div class="space-y-6 text-gray-800">
    <div>
      <h2 class="text-2xl font-bold">Thống kê cảnh báo tốc độ gió</h2>
      <p class="mt-1 text-sm text-gray-500">
        Một cảnh báo được tính khi tốc độ chuyển từ ≤300 sang &gt;300 m/s.
        Các số đo cao liên tiếp thuộc cùng một đợt cảnh báo. Thời gian theo Việt Nam.
      </p>
    </div>
    <div class="flex flex-wrap items-end gap-5 rounded-2xl bg-white p-5 border border-gray-100">
      <label class="text-sm font-medium">
        Chọn tháng
        <input v-model="month" type="month" required class="mt-2 block rounded-lg border border-gray-300 p-2" />
      </label>
      <label class="text-sm font-medium">
        Chọn ngày xem chi tiết
        <select v-model="selectedDate" class="mt-2 block rounded-lg border border-gray-300 p-2" :disabled="!days.length">
          <option v-for="day in days" :key="day.date" :value="day.date">
            {{ day.date }} · {{ day.count }} cảnh báo
          </option>
        </select>
      </label>
      <p class="pb-2 text-sm">Tổng tháng: <strong class="text-red-600">{{ totalAlerts }}</strong> cảnh báo</p>
    </div>
    <p v-if="summaryError" role="alert" class="rounded-lg bg-red-50 p-3 text-red-700">{{ summaryError }}</p>
    <p v-if="summaryLoading" role="status" class="text-sm text-gray-500">Đang tải thống kê…</p>
    <div class="rounded-2xl bg-white p-5 border border-gray-100">
      <h3 class="mb-4 font-bold">Số cảnh báo từng ngày trong tháng {{ month }}</h3>
      <div class="h-80"><Bar :data="chartData" :options="chartOptions" /></div>
      <p class="mt-3 text-xs text-gray-500">Chọn cột hoặc ngày bên dưới để xem chi tiết. Ngày không có cảnh báo hiển thị 0.</p>
      <div class="mt-4 grid grid-cols-4 sm:grid-cols-7 gap-2">
        <button v-for="day in days" :key="day.date" type="button" @click="selectedDate = day.date"
          :aria-pressed="selectedDate === day.date"
          :class="['rounded-lg border p-2 text-sm', selectedDate === day.date ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 hover:bg-blue-50']">
          Ngày {{ Number(day.date.slice(-2)) }}<br /><strong>{{ day.count }}</strong>
        </button>
      </div>
    </div>
    <div class="rounded-2xl bg-white p-5 border border-gray-100">
      <h3 class="mb-4 font-bold">Chi tiết ngày {{ selectedDate }} · {{ total }} cảnh báo</h3>
      <p v-if="error" role="alert" class="mb-3 text-red-600">{{ error }}</p>
      <p v-if="loading" role="status" class="mb-3 text-sm text-gray-500">Đang tải cảnh báo…</p>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead><tr class="border-b"><th class="p-3">ID</th><th class="p-3">Tốc độ gió</th><th class="p-3">Thời điểm bắt đầu cảnh báo</th></tr></thead>
          <tbody>
            <tr v-for="alert in rows" :key="alert.id" class="border-b border-gray-100">
              <td class="p-3">{{ alert.id }}</td><td class="p-3 font-semibold text-red-600">{{ alert.speed }} m/s</td>
              <td class="p-3"><span class="inline-flex items-center gap-2">{{ alert.recordedAt }}<CopyTimestamp :text="alert.recordedAt" /></span></td>
            </tr>
            <tr v-if="!loading && !rows.length"><td colspan="3" class="p-6 text-center text-gray-500">Không có cảnh báo trong ngày này.</td></tr>
          </tbody>
        </table>
      </div>
      <div class="mt-4 flex items-center justify-between text-sm">
        <span>Trang {{ total ? currentPage : 0 }} / {{ totalPages }}</span>
        <div class="flex gap-3">
          <button type="button" @click="prevPage" :disabled="loading || currentPage <= 1" class="rounded border px-3 py-1 disabled:opacity-40">Trước</button>
          <button type="button" @click="nextPage" :disabled="loading || currentPage >= totalPages" class="rounded border px-3 py-1 disabled:opacity-40">Sau</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import { Bar } from 'vue-chartjs'
import CopyTimestamp from '../components/CopyTimestamp.vue'
import { useWindAlerts } from '../composables/useWindAlerts.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)
const {
  month, selectedDate, days, totalAlerts, summaryError, summaryLoading,
  rows, currentPage, total, totalPages, loading, error, prevPage, nextPage,
} = useWindAlerts()
const chartData = computed(() => ({
  labels: days.value.map((day) => day.date.slice(-2)),
  datasets: [{ label: 'Số cảnh báo', data: days.value.map((day) => day.count),
    backgroundColor: days.value.map((day) => day.date === selectedDate.value ? '#2563eb' : '#f97316') }],
}))
const chartOptions = {
  responsive: true, maintainAspectRatio: false,
  scales: { x: { title: { display: true, text: 'Ngày trong tháng' } },
    y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Số cảnh báo' } } },
  onClick: (_event, elements) => {
    if (elements.length && days.value[elements[0].index]) selectedDate.value = days.value[elements[0].index].date
  },
}
</script>