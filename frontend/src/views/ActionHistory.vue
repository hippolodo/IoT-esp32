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
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <!-- Thiết bị -->
        <div>
          <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Thiết bị</label>
          <div class="relative">
            <select class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white font-medium text-gray-700">
              <option>Tất cả thiết bị</option>
              <option>Đèn Phòng Khách</option>
              <option>Đèn Phòng Ngủ</option>
              <option>Đèn Ban Công</option>
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
            <select class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white font-medium text-gray-700">
              <option>Tất cả trạng thái</option>
              <option>Success</option>
              <option>Failed</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-400">
              <i class="fa-solid fa-chevron-down text-xs"></i>
            </div>
          </div>
        </div>

        <!-- Từ thời điểm -->
        <div>
          <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Từ thời điểm</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
              <i class="fa-regular fa-calendar"></i>
            </div>
            <input type="date" class="block w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-700 font-medium" />
          </div>
        </div>

        <!-- Đến thời điểm -->
        <div>
          <label class="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wide">Đến thời điểm</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
              <i class="fa-regular fa-calendar"></i>
            </div>
            <input type="date" class="block w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-700 font-medium" />
          </div>
        </div>
      </div>

      <!-- Nút hành động -->
      <div>
        <button class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm shadow-blue-500/30">
          Lọc lịch sử
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
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">TÊN THIẾT BỊ</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">HÀNH ĐỘNG</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">TRẠNG THÁI THỰC THI</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">TRẠNG THÁI</th>
              <th class="px-6 py-4 text-[11px] font-bold text-gray-400 uppercase tracking-wider">THỜI GIAN THAO TÁC</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <!-- Row 1: Bật thành công -->
            <tr v-for="log in paginatedData" :key="log.id" class="hover:bg-gray-50/50 transition-colors">
    <td class="px-6 py-4 text-xs font-semibold text-gray-500">{{ log.id }}</td>
    
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
    
    <!-- Cột Trạng thái thực thi (Success/Failed) -->
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
        <span class="text-[11px] font-semibold text-gray-400">
            Hiển thị trang {{ currentPage }} / {{ totalPages }} (Tổng {{ actionLogs.length }} bản ghi)
        </span>
  
         <div class="flex space-x-1">
        <!-- Nút Trước -->
        <button 
        @click="prevPage"
        :disabled="currentPage === 1"
        class="px-2 py-1 text-xs font-semibold text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >Trước</button>
    
    <!-- Render các số trang 1, 2, 3... -->
        <button 
        v-for="page in totalPages" 
        :key="page"
        @click="goToPage(page)"
        :class="[
            'w-7 h-7 flex items-center justify-center text-xs rounded-md transition-colors',
            currentPage === page ? 'font-bold bg-blue-600 text-white shadow-sm' : 'font-bold text-gray-500 hover:bg-gray-100'
            ]"
        >{{ page }}</button>
    
    <!-- Nút Sau -->
        <button 
        @click="nextPage"
        :disabled="currentPage === totalPages"
        class="px-2 py-1 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >Sau</button>
        </div>
    </div>
    </div>
  </div>
</template>

<script setup>
    import { ref, computed } from 'vue'

// 1. Tạo 25 bản ghi dữ liệu giả (Mock data)
const actionLogs = ref(
  Array.from({ length: 25 }).map((_, index) => {
    // Random trạng thái thành công/thất bại và bật/tắt
    const isSuccess = Math.random() > 0.15; // 85% thành công
    const isOn = Math.random() > 0.5; // 50% bật, 50% tắt
    
    // Xoay vòng 3 thiết bị
    const devices = [
      { name: 'Đèn Phòng Khách', gpio: 'GPIO 18' },
      { name: 'Đèn Phòng Ngủ', gpio: 'GPIO 19' },
      { name: 'Đèn Ban Công', gpio: 'GPIO 21' }
    ];
    const device = devices[index % 3];

    return {
        id: `#LOG-0${189 - index}`,
        deviceName: device.name,
        gpio: device.gpio,
        isIconActive: isOn,
        action: isOn ? 'BẬT (ON)' : 'TẮT (OFF)',
        actionClass: isOn ? 'text-emerald-500' : 'text-gray-400',
        execStatus: isSuccess ? 'SUCCESS' : 'FAILED',
        execStatusColor: isSuccess ? 'bg-emerald-500' : 'bg-red-500',
        execStatusTextClass: isSuccess ? 'text-gray-700' : 'text-red-500',
        deviceStatus: isOn ? 'BẬT' : 'TẮT',
        deviceStatusColor: isOn ? 'bg-emerald-500' : 'bg-gray-300',
        date: '2026-10-06', // Lấy ngày hiện tại trong ngữ cảnh
        time: `10:${55 - (index % 55)}:15`
    }
    })
    )

// --- LOGIC PHÂN TRANG ---
    const currentPage = ref(1)
    const itemsPerPage = 10 // Cố định 10 dòng / trang

    const totalPages = computed(() => Math.ceil(actionLogs.value.length / itemsPerPage))

    const paginatedData = computed(() => {
    const start = (currentPage.value - 1) * itemsPerPage
    const end = start + itemsPerPage
    return actionLogs.value.slice(start, end)
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