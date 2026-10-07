<template>
  <div class="animate-fade-in text-gray-800">
    <!-- Header: Tiêu đề và Trạng thái -->
    <div class="flex justify-between items-start mb-8">
      <div>
        <h2 class="text-2xl font-bold">Dashboard Tổng Quan</h2>
        <p class="text-sm text-gray-500 mt-1">Cập nhật dữ liệu cảm biến và điều khiển thiết bị theo thời gian thực</p>
      </div>
      <!-- Nút trạng thái ESP32 -->
      <div class="flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-full border border-blue-100">
        <span class="relative flex h-3 w-3">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
        </span>
        <span class="text-sm font-semibold text-blue-600">ESP32 Connected</span>
      </div>
    </div>

    <!-- Hàng 1: 3 Thẻ Thông Kê (Nhiệt độ, Độ ẩm, Ánh sáng) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <!-- Card Nhiệt độ -->
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400 tracking-wider ">NHIỆT ĐỘ</span>
          <div class="w-8 h-8 rounded-full bg-red-50 text-red-500 flex items-center justify-center">
            <i class="fa-solid fa-temperature-half"></i>
          </div>
        </div>
        <div class="flex items-baseline space-x-1">
          <span class="text-4xl font-bold">28.5</span>
          <span class="text-xl text-gray-500">°C</span>
        </div>
        <!-- <div class="mt-4 text-xs font-medium text-red-500 flex items-center">
          <i class="fa-solid fa-arrow-trend-up mr-1"></i> +0.2°C so với vừa rồi
        </div> -->
      </div>

      <!-- Card Độ ẩm -->
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400 tracking-wider uppercase">Độ Ẩm</span>
          <div class="w-8 h-8 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center">
            <i class="fa-solid fa-droplet"></i>
          </div>
        </div>
        <div class="flex items-baseline space-x-1">
          <span class="text-4xl font-bold">65</span>
          <span class="text-xl text-gray-500">%</span>
        </div>
        <!-- <div class="mt-4 text-xs font-medium text-emerald-500 flex items-center">
          <i class="fa-regular fa-circle-check mr-1"></i> Mức độ lý tưởng
        </div> -->
      </div>

      <!-- Card Ánh sáng -->
      <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex justify-between items-center mb-4">
          <span class="text-xs font-bold text-gray-400 tracking-wider uppercase">Ánh Sáng</span>
          <div class="w-8 h-8 rounded-full bg-amber-50 text-amber-500 flex items-center justify-center">
            <i class="fa-regular fa-sun"></i>
          </div>
        </div>
        <div class="flex items-baseline space-x-1">
          <span class="text-4xl font-bold">420</span>
          <span class="text-xl text-gray-500">Lux</span>
        </div>
        <!-- <div class="mt-4 text-xs font-medium text-amber-500 flex items-center">
          <i class="fa-solid fa-sun mr-1"></i> Ánh sáng tự nhiên tốt
        </div> -->
      </div>
    </div>

    <!-- Hàng 2: Biểu đồ và Cụm điều khiển -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Cột trái: Biểu đồ (Chiếm 2 phần) -->
      <div class="lg:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div class="flex items-center mb-6">
          <i class="fa-solid fa-chart-line text-blue-500 mr-2 text-lg"></i>
          <h3 class="text-lg font-bold">Biểu Đồ Cảm Biến Realtime</h3>
        </div>
        
        <!-- Khung chứa biểu đồ -->
        <div class="h-96 w-full relative">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- Cột phải: Cụm điều khiển đèn (Chiếm 1 phần) -->
      <div class="lg:col-span-1 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div class="flex items-center mb-6">
          <i class="fa-regular fa-lightbulb text-amber-500 mr-2 text-lg"></i>
          <h3 class="text-lg font-bold">Điều Khiển Đèn</h3>
        </div>

        <div class="space-y-4">
          <!-- Vòng lặp render các công tắc đèn -->
          <div v-for="lamp in lamps" :key="lamp.id" 
               class="flex items-center justify-between p-4 rounded-xl border border-gray-50 bg-gray-50/50 hover:bg-gray-50 transition-colors">
            
            <div class="flex items-center space-x-3">
              <div :class="['w-10 h-10 rounded-full flex items-center justify-center transition-colors', 
                           lamp.isOn ? 'bg-blue-100 text-blue-600' : 'bg-white text-gray-400 border border-gray-200']">
                <i class="fa-regular fa-lightbulb text-lg"></i>
              </div>
              <div>
                <p class="text-sm font-bold">{{ lamp.name }}</p>
                <p class="text-xs text-gray-500">{{ lamp.gpio }}</p>
              </div>
            </div>

            <!-- Nút Toggle Switch -->
            <button 
              @click="toggleLamp(lamp)"
              :class="['relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                       lamp.isOn ? 'bg-blue-600' : 'bg-gray-200']"
            >
              <span class="sr-only">Toggle {{ lamp.name }}</span>
              <span 
                :class="['pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                         lamp.isOn ? 'translate-x-5' : 'translate-x-0']"
              ></span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Line } from 'vue-chartjs'

// Đăng ký các thành phần của Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

// --- QUẢN LÝ TRẠNG THÁI ĐÈN ---
const lamps = ref([
  { id: 1, name: 'Đèn Phòng Khách', gpio: 'GPIO 18', isOn: true },
  { id: 2, name: 'Đèn Phòng Ngủ', gpio: 'GPIO 19', isOn: false },
  { id: 3, name: 'Đèn Ban Công', gpio: 'GPIO 21', isOn: true },
])

const toggleLamp = (lamp) => {
  lamp.isOn = !lamp.isOn
  // Gửi API đến backend để điều khiển ESP32 tại đây
  console.log(`Đã chuyển trạng thái ${lamp.name} thành ${lamp.isOn ? 'BẬT' : 'TẮT'}`)
}

// --- CẤU HÌNH BIỂU ĐỒ ---
const chartData = ref({
  labels: ['10:00', '10:05', '10:10', '10:15', '10:20', '10:25', '10:30', '10:35', '10:40', '10:45'],
  datasets: [
    {
      label: 'Nhiệt độ (°C)',
      borderColor: '#ef4444', // Red-500
      backgroundColor: '#ef4444',
      data: [28.0, 28.2, 28.5, 29.1, 28.8, 28.5, 28.3, 28.4, 28.5, 28.5],
      tension: 0.4,
      yAxisID: 'y'
    },
    {
      label: 'Độ ẩm (%)',
      borderColor: '#3b82f6', // Blue-500
      backgroundColor: '#3b82f6',
      data: [60, 62, 65, 63, 61, 64, 66, 65, 65, 65],
      tension: 0.4,
      yAxisID: 'y1'
    },
    {
      label: 'Ánh sáng (Lux)',
      borderColor: '#f59e0b', // Amber-500
      backgroundColor: '#f59e0b',
      data: [380, 400, 420, 450, 430, 410, 400, 415, 420, 420],
      tension: 0.4,
      yAxisID: 'y2'
    }
  ]
})

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
        font: { family: 'Inter, sans-serif', size: 12 }
      }
    }
  },
  scales: {
    x: {
      grid: { display: false }
    },
    y: {
      type: 'linear',
      display: true,
      position: 'left',
      title: { display: true, text: 'Nhiệt độ & Độ ẩm' },
      grid: { borderDash: [4, 4] }
    },
    y1: {
      type: 'linear',
      display: false, // Ẩn bớt trục Y của độ ẩm cho đỡ rối, dùng chung scale với nhiệt độ
      position: 'left'
    },
    y2: {
      type: 'linear',
      display: true,
      position: 'right',
      title: { display: true, text: 'Ánh sáng (Lux)' },
      grid: { display: false }
    }
  }
})
</script>

<style scoped>
/* Thêm hiệu ứng fade-in nhẹ khi chuyển trang */
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>