<template>
  <div class="animate-fade-in text-gray-800 font-sans">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-[#1a1d2e]">Lịch Sử Dữ Liệu Cảm Biến</h2>
      <p class="text-sm text-gray-500 mt-1">Tra cứu thông số đo nhiệt độ, độ ẩm và ánh sáng từ cơ sở dữ liệu</p>
    </div>

    <!-- Khu vực Bộ lọc (Filter) -->
    <div class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-5">
        
        <!-- Dropdown Loại cảm biến -->
        <div>
          <label class="block text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide">Loại Cảm Biến</label>
          <div class="relative">
            <select class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white">
              <option>Tất cả cảm biến</option>
              <option>Nhiệt độ (Temperature)</option>
              <option>Độ ẩm (Humidity)</option>
              <option>Ánh sáng (Light)</option>
              <option>Thời gian</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
              <i class="fa-solid fa-chevron-down text-xs"></i>
            </div>
          </div>
        </div>

        <!-- Input Thời gian bắt đầu -->
        <div>
          <label class="block text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide">Thời gian bắt đầu</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
              <i class="fa-regular fa-calendar"></i>
            </div>
            <input type="datetime-local" value="2026-08-19T10:00" class="block w-full pl-10 pr-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white" />
          </div>
        </div>

        <!-- Input Thời gian kết thúc -->
        <div>
          <label class="block text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide">Thời gian kết thúc</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
              <i class="fa-regular fa-calendar"></i>
            </div>
            <input type="datetime-local" value="2026-08-19T11:00" class="block w-full pl-10 pr-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white" />
          </div>
        </div>
      </div>

      <!-- Nút hành động -->
      <div class="flex space-x-3">
        <button class="flex items-center px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm shadow-blue-500/30">
          <i class="fa-solid fa-magnifying-glass mr-2 text-xs"></i> Tìm kiếm
        </button>
        <button class="flex items-center px-5 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg transition-colors shadow-sm">
          <i class="fa-solid fa-rotate-right mr-2 text-xs"></i> Làm mới
        </button>
      </div>
    </div>

    <!-- Bảng Dữ Liệu -->
    <div class="bg-white rounded-2xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 border-b border-gray-200">
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-20">#ID</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Tên Cảm Biến</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Loại Cảm Biến</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Giá Trị Đo</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Thời Gian Ghi Nhận</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <!-- Row 1 -->
            <tr v-for="item in paginatedData" :key="item.id" class="hover:bg-blue-50/30 transition-colors">
                <td class="px-6 py-4 text-sm text-gray-500">{{ item.id }}</td>
                <td class="px-6 py-4 text-sm font-semibold text-gray-800">{{ item.name }}</td>
                <td class="px-6 py-4">
                <span :class="['inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border', item.typeClass]">
                    <i :class="['fa-solid mr-1.5', item.icon]"></i> {{ item.type }}
                </span>
                </td>
                <td class="px-6 py-4 text-sm font-bold text-gray-800">{{ item.value }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ item.time }}</td>
            </tr>
            <!-- Row 2 -->
           
            <!-- Row 3 -->
            <!-- <tr class="hover:bg-blue-50/30 transition-colors">
              <td class="px-6 py-4 text-sm text-gray-500">1040</td>
              <td class="px-6 py-4 text-sm font-semibold text-gray-800">LDR_Garden</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-600 border border-indigo-200/50">
                  <i class="fa-regular fa-sun mr-1.5 text-[10px]"></i> LIGHT
                </span>
              </td>
              <td class="px-6 py-4 text-sm font-bold text-gray-800">420 Lux</td>
              <td class="px-6 py-4 text-sm text-gray-500">2026-08-19 10:45:00</td>
            </tr> -->
          </tbody>
        </table>
      </div>

      <!-- Phân trang (Pagination) -->
        <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex items-center justify-between">
    <!-- Hiển thị thông tin trang động -->
            <span class="text-xs font-medium text-gray-500">
                Hiển thị trang {{ currentPage }} / {{ totalPages }} (Tổng {{ sensorHistories.length }} bản ghi)
            </span>
            
            <div class="flex space-x-1">
                <!-- Nút Trước (Vô hiệu hóa nếu đang ở trang 1) -->
                <button 
                @click="prevPage" 
                :disabled="currentPage === 1"
                class="px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >Trước</button>
                
                <!-- Vòng lặp hiển thị các số trang (1, 2, 3...) -->
                <button 
                v-for="page in totalPages" 
                :key="page"
                @click="goToPage(page)"
                :class="[
                    'w-8 h-8 flex items-center justify-center text-sm rounded-md transition-colors',
                    currentPage === page ? 'font-bold bg-blue-600 text-white shadow-sm' : 'font-medium text-gray-600 hover:bg-gray-200'
                ]"
                >{{ page }}</button>
                
                <!-- Nút Sau (Vô hiệu hóa nếu đang ở trang cuối) -->
                <button 
                @click="nextPage"
                :disabled="currentPage === totalPages"
                class="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >Sau</button>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// 1. Tạo 25 bản ghi dữ liệu giả (Mock data) để test phân trang
const sensorHistories = ref(
  Array.from({ length: 25 }).map((_, index) => {
    const types = [
      { type: 'TEMPERATURE', icon: 'fa-temperature-half', class: 'bg-red-100 text-red-600', val: '28.5 °C' },
      { type: 'HUMIDITY', icon: 'fa-droplet', class: 'bg-blue-100 text-blue-600', val: '65.0 %' },
      { type: 'LIGHT', icon: 'fa-sun', class: 'bg-indigo-100 text-indigo-600', val: '420 Lux' }
    ];
    const t = types[index % 3];
    return {
      id: 1042 - index,
      name: index % 3 === 2 ? 'LDR_Garden' : 'DHT11_LivingRoom',
      type: t.type,
      value: t.val,
      time: `2026-10-06 10:${55 - index}:00`,
      typeClass: t.class,
      icon: t.icon
    }
  })
)

// --- LOGIC PHÂN TRANG ---
const currentPage = ref(1)
const itemsPerPage = 10 // Cố định 10 bản ghi 1 trang

// Tính tổng số trang
const totalPages = computed(() => {
  return Math.ceil(sensorHistories.value.length / itemsPerPage)
})

// Lọc ra 10 bản ghi tương ứng với trang hiện tại
const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return sensorHistories.value.slice(start, end)
})

// Các hàm chuyển trang
const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++
}
const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--
}
const goToPage = (page) => {
  currentPage.value = page
}
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