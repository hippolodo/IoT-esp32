<template>
  <div class="animate-fade-in text-gray-800 font-sans">
    <!-- Header -->
    <div class="flex justify-between items-start mb-6">
      <div>
        <h2 class="text-2xl font-bold text-[#1a1d2e]">Lịch Sử Thao Tác Thiết Bị</h2>
        <p class="text-sm text-gray-500 mt-1">Nhật ký kiểm toán toàn bộ thao tác bật/tắt bóng đèn qua giao diện và ESP32</p>
      </div>
      <ConnectionStatus />
    </div>

    <!-- Khu vực Bộ lọc (Filter) -->

    <div class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 mb-6">
    <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-5">

        <!-- Thiết bị -->
        <div>
        <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Thiết bị</label>
        <div class="relative">
            <select v-model="searchDevice" class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white font-medium text-gray-700">
            <option value="all">Tất cả thiết bị</option>
            <option v-for="device in system.devices" :key="device.id" :value="device.id">{{ device.name }}</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-400">
            <i class="fa-solid fa-chevron-down text-xs"></i>
            </div>
        </div>
        </div>

        <!-- Trạng thái thực thi -->
        <div>
        <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Trạng thái thực thi</label>
        <div class="relative">
            <select v-model="searchStatus" class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white font-medium text-gray-700">
            <option value="all">Tất cả trạng thái</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">PENDING</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-400">
            <i class="fa-solid fa-chevron-down text-xs"></i>
            </div>
        </div>
        </div>
        <div>
            <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Hành động</label>
            <div class="relative">
            <select v-model="searchAction" class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white font-medium text-gray-700">
                <option value="all">Tất cả hành động</option>
                <option value="ON">BẬT (ON)</option>
                <option value="OFF">TẮT (OFF)</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-400">
                <i class="fa-solid fa-chevron-down text-xs"></i>
            </div>
        </div>
  </div>
        <!-- Từ thời điểm -->
       <!-- Thời gian (Đã gộp thành 1 ô) -->
        <div>
        <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Thời gian</label>
        <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
            <i class="fa-solid fa-magnifying-glass"></i>
            </div>
            <input type="text" v-model="searchTime" placeholder="VD: 2026-10-18 hoặc 2026-10-18 17:30" @keyup.enter="handleSearch" class="block w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-700 font-medium" />
        </div>
        </div>
    </div>

    <!-- Nút hành động -->
    <div class="flex space-x-3">
        <button @click="handleSearch" class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm shadow-blue-500/30">
        Lọc lịch sử
        </button>
        <button @click="handleReset" class="px-6 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-semibold rounded-lg transition-colors shadow-sm">
        Làm mới
        </button>
    </div>
    </div>

    <p v-if="error" role="alert" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <p v-if="loading" role="status" class="mb-3 text-sm text-gray-500">Đang tải lịch sử…</p>
    <!-- Bảng Dữ Liệu -->
    <div class="bg-white rounded-2xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider w-24">#LOG ID</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">USER ID</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">TÊN THIẾT BỊ</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">HÀNH ĐỘNG</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">TRẠNG THÁI THỰC THI</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">KẾT QUẢ LỆNH</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider" :aria-sort="timeSortDirection === 'asc' ? 'ascending' : 'descending'">
                <button type="button" @click="toggleTimeSort" class="inline-flex items-center gap-2 hover:text-blue-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 rounded" :title="timeSortDirection === 'desc' ? 'Đang mới nhất trước. Bấm để xem cũ nhất trước' : 'Đang cũ nhất trước. Bấm để xem mới nhất trước'">
                  THỜI GIAN THAO TÁC
                  <i :class="['fa-solid', timeSortDirection === 'asc' ? 'fa-arrow-up' : 'fa-arrow-down']" aria-hidden="true"></i>
                </button>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-if="!loading && !paginatedData.length"><td colspan="7" class="p-8 text-center text-sm text-gray-500">Không có lịch sử phù hợp.</td></tr>
            <tr v-for="log in paginatedData" :key="log.id" class="hover:bg-gray-50/50 transition-colors">
    <td class="px-6 py-4 text-xs font-semibold text-gray-500">{{ log.id }}</td>
    <td class="px-6 py-4 text-sm font-semibold text-gray-700">
      <div class="flex items-center space-x-2">
        <i class="fa-solid fa-user-circle text-gray-400"></i>
        <span>{{ log.userId }}</span>
      </div>
    </td>
    <!-- Cột tên thiết bị & Icon -->
    <td class="px-6 py-4">
      <div class="flex items-center space-x-3">
        <div :class="['w-8 h-8 rounded-full flex items-center justify-center border',
            log.isIconActive ? 'bg-blue-50 text-blue-500 border-transparent' : 'bg-gray-50 text-gray-400 border-gray-100']">
            <i class="fa-regular fa-lightbulb text-sm"></i>
        </div>
        <div>
          <p class="text-sm font-bold text-gray-800">{{ log.deviceName }}</p>
          <p class="text-xs text-gray-400">({{ log.gpio }})</p>
        </div>
      </div>
    </td>

    <!-- Cột Hành động -->
    <td :class="['px-6 py-4 text-sm font-bold', log.actionClass]">{{ log.action }}</td>

    <!-- Cột Trạng thái thực thi (Success/Failed/Pending) -->
    <td class="px-6 py-4">
      <div :class="['flex items-center text-xs font-bold', log.execStatusTextClass]">
        <span :class="['w-1.5 h-1.5 rounded-full mr-2', log.execStatusColor]"></span> {{ log.execStatus }}
      </div>
    </td>

    <!-- Cột Trạng thái cuối (Bật/Tắt) -->
    <td class="px-6 py-4">
      <div :class="['flex items-center text-xs font-bold', log.isIconActive ? 'text-gray-700' : 'text-gray-400']">
        <span :class="['w-1.5 h-1.5 rounded-full mr-2', log.deviceStatusColor]"></span> {{ log.deviceStatus }}
      </div>
    </td>

    <!-- Cột Thời gian -->
    <td class="px-6 py-4 text-sm font-medium text-gray-500">
      {{ log.date }}<br><span class="text-xs text-gray-400">{{ log.time }}</span>
    </td>
  </tr>
          </tbody>
        </table>
      </div>

      <!-- Phân trang (Pagination) -->
      <div class="px-6 py-4 bg-white border-t border-gray-100 flex items-center justify-between">
  <!-- Hiển thị Text động -->
        <div class="flex items-center space-x-6">
    <span class="text-[11px] font-semibold text-gray-400">
      Hiển thị trang {{ total === 0 ? 0 : currentPage }} / {{ totalPages }} (Tổng {{ total }} bản ghi)
    </span>

    <!-- THÊM MỚI: Ô Dropdown chọn size -->
    <div class="flex items-center space-x-2">
      <span class="text-[11px] font-bold text-gray-500 uppercase">Số dòng:</span>
      <select
        v-model="itemsPerPage"
        @change="handleSizeChange"
        class="text-xs font-semibold text-gray-600 bg-gray-50 border border-gray-200 rounded-md px-2 py-1 outline-none cursor-pointer hover:bg-gray-100 transition-colors"
      >
        <option :value="5">5 dòng</option>
        <option :value="8">8 dòng</option>
        <option :value="10">10 dòng</option>
        <option :value="20">20 dòng</option>
        <option :value="50">50 dòng</option>
      </select>
    </div>
  </div>

  <!-- CỤM PHẢI: Các nút chuyển trang (Giữ nguyên) -->
    <div class="flex space-x-1">
        <button @click="prevPage" :disabled="currentPage <= 1 || loading" class="px-2 py-1 text-xs font-semibold text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50">Trước</button>

        <button
        v-for="page in visiblePages"
        :key="page"
        @click="goToPage(page)"
        :class="['w-7 h-7 flex items-center justify-center text-xs rounded-md transition-colors', currentPage === page ? 'font-bold bg-blue-600 text-white shadow-sm' : 'font-bold text-gray-500 hover:bg-gray-100']"
        >{{ page }}</button>

        <button @click="nextPage" :disabled="currentPage >= totalPages || loading" class="px-2 py-1 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors disabled:opacity-50">Sau</button>
    </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import { system } from '../services/system'
import { usePage } from '../composables/usePage'
const searchDevice = ref('all'), searchStatus = ref('all'), searchAction = ref('all'), searchTime = ref('')
const applied = ref({ device: 'all', status: 'all', action: 'all', time: '' })
const timeSortDirection = ref('desc')
const { rows, currentPage, itemsPerPage, total, totalPages, visiblePages, loading, error,
  load, handleSizeChange, goToPage, nextPage, prevPage } = usePage('/api/history', () => ({
    deviceId: applied.value.device === 'all' ? undefined : applied.value.device,
    status: applied.value.status === 'all' ? undefined : applied.value.status,
    action: applied.value.action === 'all' ? undefined : applied.value.action,
    startTime: applied.value.time, endTime: applied.value.time, sort: timeSortDirection.value,
  }), '/topic/device-status')
const paginatedData = computed(() => rows.value.map(row => {
  const isOn = row.action === 'ON', success = row.status === 'SUCCESS'
  const device = system.devices.find(device => device.id === row.deviceId)
  return { id: `#LOG-${row.id}`, userId: row.userId ?? '—', deviceName: row.deviceName,
    gpio: device ? `GPIO ${device.controlPin ?? device.pinGpio ?? '—'}` : '—',
    isIconActive: success && isOn, action: isOn ? 'BẬT (ON)' : 'TẮT (OFF)',
    actionClass: isOn ? 'text-emerald-500' : 'text-gray-400', execStatus: row.status,
    execStatusColor: row.status === 'PENDING' ? 'bg-amber-500' : success ? 'bg-emerald-500' : 'bg-red-500',
    execStatusTextClass: row.status === 'PENDING' ? 'text-amber-600' : success ? 'text-gray-700' : 'text-red-500',
    deviceStatus: success ? (isOn ? 'BẬT' : 'TẮT') : 'Chưa xác nhận',
    deviceStatusColor: success ? 'bg-emerald-500' : 'bg-gray-300',
    date: row.timestamp.split(' ')[0], time: row.timestamp.split(' ')[1] || '',
  }
}))
const handleSearch = () => {
  applied.value = { device: searchDevice.value, status: searchStatus.value, action: searchAction.value,
    time: searchTime.value.trim().replace(/[Tt]/g, ' ').replace(/\s+/g, ' ') }
  currentPage.value = 1
  load()
}
const handleReset = () => { searchDevice.value = searchStatus.value = searchAction.value = 'all'; searchTime.value = ''; handleSearch() }
const toggleTimeSort = () => { timeSortDirection.value = timeSortDirection.value === 'desc' ? 'asc' : 'desc'; currentPage.value = 1; load() }
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
