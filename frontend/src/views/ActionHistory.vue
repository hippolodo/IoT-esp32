<template>
  <div class="animate-fade-in text-gray-800 font-sans">
    <!-- Header -->
    <div class="flex justify-between items-start mb-6">
      <div>
        <h2 class="text-2xl font-bold text-[#1a1d2e]">Lịch Sử Thao Tác Thiết Bị</h2>
        <p class="text-sm text-gray-500 mt-1">Nhật ký kiểm toán toàn bộ thao tác bật/tắt bóng đèn qua giao diện và ESP32</p>
      </div>
      <div class="flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-full border border-blue-100">
        <span class="relative flex h-3 w-3">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
        </span>
        <span class="text-sm font-semibold text-blue-600">ESP32 Connected</span>
      </div>
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
            <option value="Đèn Phòng Khách">Đèn Phòng Khách</option>
            <option value="Đèn Phòng Ngủ">Đèn Phòng Ngủ</option>
            <option value="Đèn Ban Công">Đèn Ban Công</option>
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
                <option value="BẬT (ON)">BẬT (ON)</option>
                <option value="TẮT (OFF)">TẮT (OFF)</option>
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
            <input type="text" v-model="searchTime" placeholder="Nhập ngày hoặc giờ từ bảng" @keyup.enter="handleSearch" class="block w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-700 font-medium" />
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
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">TRẠNG THÁI</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider" :aria-sort="timeSortDirection === 'asc' ? 'ascending' : 'descending'">
                <button type="button" @click="toggleTimeSort" class="inline-flex items-center gap-2 hover:text-blue-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 rounded" :title="timeSortDirection === 'desc' ? 'Đang mới nhất trước. Bấm để xem cũ nhất trước' : 'Đang cũ nhất trước. Bấm để xem mới nhất trước'">
                  THỜI GIAN THAO TÁC
                  <i :class="['fa-solid', timeSortDirection === 'asc' ? 'fa-arrow-up' : 'fa-arrow-down']" aria-hidden="true"></i>
                </button>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
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
      Hiển thị trang {{ filteredData.length === 0 ? 0 : currentPage }} / {{ totalPages }} (Tổng {{ filteredData.length }} bản ghi)
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
        <button @click="prevPage" :disabled="currentPage === 1" class="px-2 py-1 text-xs font-semibold text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50">Trước</button>
        
        <button 
        v-for="page in totalPages" 
        :key="page"
        @click="goToPage(page)"
        :class="['w-7 h-7 flex items-center justify-center text-xs rounded-md transition-colors', currentPage === page ? 'font-bold bg-blue-600 text-white shadow-sm' : 'font-bold text-gray-500 hover:bg-gray-100']"
        >{{ page }}</button>
        
        <button @click="nextPage" :disabled="currentPage === totalPages" class="px-2 py-1 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors disabled:opacity-50">Sau</button>
    </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// 1. Tạo 45 bản ghi dữ liệu giả (Mock data)
const actionLogs = ref(
  Array.from({ length: 45 }).map((_, index) => {
    const isSuccess = Math.random() > 0.15; // 85% thành công
    const execStatus = index % 10 === 0 ? 'PENDING' : (isSuccess ? 'SUCCESS' : 'FAILED');
    const isOn = Math.random() > 0.5; // 50% bật, 50% tắt
    
    const devices = [
      { name: 'Đèn Phòng Khách', gpio: 'GPIO 18' },
      { name: 'Đèn Phòng Ngủ', gpio: 'GPIO 19' },
      { name: 'Đèn Ban Công', gpio: 'GPIO 21' }
    ];
    const device = devices[index % 3];

    const mockUsers = ['admin', 'system', 'hiep_nv'];
    const user = mockUsers[index % mockUsers.length]
    // Sinh thời gian lùi dần về quá khứ (mỗi bản ghi cách nhau 15 phút)
    const dateObj = new Date();
    dateObj.setMinutes(dateObj.getMinutes() - index * 15);
    const dateStr = `${dateObj.getFullYear()}-${String(dateObj.getMonth()+1).padStart(2,'0')}-${String(dateObj.getDate()).padStart(2,'0')}`;
    const timeStr = `${String(dateObj.getHours()).padStart(2,'0')}:${String(dateObj.getMinutes()).padStart(2,'0')}:${String(dateObj.getSeconds()).padStart(2,'0')}`;

    return {
      id: `#LOG-0${200 - index}`,
      userId: user,
      deviceName: device.name,
      gpio: device.gpio,
      isIconActive: isOn,
      action: isOn ? 'BẬT (ON)' : 'TẮT (OFF)',
      actionClass: isOn ? 'text-emerald-500' : 'text-gray-400',
      execStatus,
      execStatusColor: execStatus === 'PENDING' ? 'bg-amber-500' : (isSuccess ? 'bg-emerald-500' : 'bg-red-500'),
      execStatusTextClass: execStatus === 'PENDING' ? 'text-amber-600' : (isSuccess ? 'text-gray-700' : 'text-red-500'),
      deviceStatus: isOn ? 'BẬT' : 'TẮT',
      deviceStatusColor: isOn ? 'bg-emerald-500' : 'bg-gray-300',
      date: dateStr,
      time: timeStr
    }
  })
)

// --- TRẠNG THÁI FORM TÌM KIẾM ---
const searchDevice = ref('all')
const searchStatus = ref('all')
const searchAction = ref('all')
const searchTime = ref('')  

const appliedFilters = ref({
  device: 'all',
  status: 'all',
  action: 'all',
  time: ''
})

// Bấm "Lọc lịch sử"
const handleSearch = () => {
  appliedFilters.value = {
    device: searchDevice.value,
    status: searchStatus.value,
   action: searchAction.value,
    time: searchTime.value.trim().replace(/[Tt]/g, ' ').replace(/\s+/g, ' ')
  }
  currentPage.value = 1
}

// Bấm "Làm mới"
const handleReset = () => {
  searchDevice.value = 'all'
  searchStatus.value = 'all'
  searchAction.value = 'all'
  searchTime.value = ''
  appliedFilters.value = { device: 'all', status: 'all', action: 'all', time: '' }
  currentPage.value = 1
}

// --- LOGIC LỌC DỮ LIỆU ---
const filteredData = computed(() => {
  return actionLogs.value.filter(log => {
    const filters = appliedFilters.value;
    
    // 1. Lọc theo Tên Thiết Bị
    if (filters.device !== 'all' && log.deviceName !== filters.device) return false;
    if (filters.status !== 'all' && log.execStatus !== filters.status) return false;
    if (filters.action !== 'all' && log.action !== filters.action) return false;
    
    // 5. LỌC THEO 1 MỐC THỜI GIAN (Tìm kiếm tương đối)
    if (filters.time) {
      // Gộp date và time của log lại để so sánh
      const logDateTime = `${log.date} ${log.time}`; 
      
      if (!logDateTime.includes(filters.time)) {
        return false;
      }
    }
    return true;
  })
})

// --- SẮP XẾP THỜI GIAN TRƯỚC KHI PHÂN TRANG ---
const timeSortDirection = ref('desc')

const toggleTimeSort = () => {
  timeSortDirection.value = timeSortDirection.value === 'desc' ? 'asc' : 'desc'
  currentPage.value = 1
}

const sortedData = computed(() => {
  return [...filteredData.value].sort((a, b) => {
    // Ngày YYYY-MM-DD và giờ HH:mm:ss có thứ tự chuỗi giống thứ tự thời gian.
    const aTime = `${a.date} ${a.time}`
    const bTime = `${b.date} ${b.time}`
    const comparison = aTime.localeCompare(bTime)
    return timeSortDirection.value === 'asc' ? comparison : -comparison
  })
})

// --- LOGIC PHÂN TRANG (Dựa trên dữ liệu ĐÃ LỌC VÀ SẮP XẾP) ---
const currentPage = ref(1)
const itemsPerPage = ref(8)

const handleSizeChange = () => {
  currentPage.value = 1
}

const totalPages = computed(() => Math.ceil(filteredData.value.length / itemsPerPage.value) || 1)

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  return sortedData.value.slice(start, start + itemsPerPage.value)
})

const nextPage = () => { if (currentPage.value < totalPages.value) currentPage.value++ }
const prevPage = () => { if (currentPage.value > 1) currentPage.value-- }
const goToPage = (page) => { currentPage.value = page }
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
