<template>
  <div class="animate-fade-in text-gray-800 font-sans">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-[#1a1d2e]">Lịch Sử Dữ Liệu Cảm Biến</h2>
      <p class="text-sm text-gray-500 mt-1">Tra cứu thông số đo nhiệt độ, độ ẩm và ánh sáng từ cơ sở dữ liệu</p>
    </div>

    <!-- Khu vực Bộ lọc (Filter) -->
    <div class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-5">
        
        <!-- Dropdown Loại cảm biến -->
        <div>
          <label class="block text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide">Loại Cảm Biến</label>
          <div class="relative">
            <select v-model="searchType" class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white">
                <option value="all">Tất cả cảm biến</option>
                <option value="TEMPERATURE">Nhiệt độ (Temperature)</option>
                <option value="HUMIDITY">Độ ẩm (Humidity)</option>
                <option value="LIGHT">Ánh sáng (Light)</option>
                <option value="TIME">Thời gian</option>
            </select>
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
              <i class="fa-solid fa-chevron-down text-xs"></i>
            </div>
          </div>
        </div>

        <div>
            <label class="block text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide">Tìm Kiếm</label>
            <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
                <i class="fa-solid fa-magnifying-glass text-xs"></i>
            </div>
            <input 
                type="text" 
                v-model="searchValue" 
                @keyup.enter="handleSearch"
                :placeholder="searchType === 'TIME' ? 'Nhập ngày hoặc giờ từ bảng' : 'VD: 28.4, 66, 400...'"
                class="block w-full pl-9 pr-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white transition-colors" 
            />
            </div>
        </div>
      </div>

      <!-- Nút hành động -->
      <div class="flex space-x-3">
       <button @click="handleSearch" class="flex items-center px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm shadow-blue-500/30">
          <i class="fa-solid fa-magnifying-glass mr-2 text-xs"></i> Tìm kiếm
        </button>
        <button @click="handleReset" class="flex items-center px-5 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg transition-colors shadow-sm">
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
          </tbody>
        </table>
      </div>

      <!-- Phân trang (Pagination) -->
        <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex items-center justify-between">
    <!-- Hiển thị thông tin trang động -->
           <div class="flex items-center space-x-6">
    <span class="text-[11px] font-semibold text-gray-400">
      Hiển thị trang {{ filteredData.length === 0 ? 0 : currentPage }} / {{ totalPages }} (Tổng {{ filteredData.length }} bản ghi)
    </span>
    
    <!-- Ô dropdown chọn Page Size -->
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
        <option :value="100">100 dòng</option>
      </select>
    </div>
  </div>
  
  <!-- Cụm bên phải: Các nút chuyển trang 1, 2, 3... -->
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

// 1. Mảng dữ liệu giả (Mô phỏng 45 bản ghi liên tiếp)
const sensorHistories = ref(
  Array.from({ length: 45 }).map((_, index) => {
    const types = [
      { type: 'TEMPERATURE', icon: 'fa-temperature-half', class: 'bg-red-100 text-red-600 border-red-200/50', val: `${(28.0 + Math.random()*2).toFixed(1)} °C` },
      { type: 'HUMIDITY', icon: 'fa-droplet', class: 'bg-blue-100 text-blue-600 border-blue-200/50', val: `${Math.floor(60 + Math.random()*10)}.0 %` },
      { type: 'LIGHT', icon: 'fa-sun', class: 'bg-indigo-100 text-indigo-600 border-indigo-200/50', val: `${Math.floor(400 + Math.random()*50)} Lux` }
    ];
    const t = types[index % 3];
    
    // Sinh thời gian giảm dần (Cách nhau 5 phút)
    const date = new Date();
    date.setMinutes(date.getMinutes() - index * 5);
    const timeString = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')} ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}:00`;

    return {
      id: 1045 - index,
      name: index % 3 === 2 ? 'LDR_Garden' : 'DHT11_LivingRoom',
      type: t.type,
      value: t.val,
      time: timeString,
      typeClass: t.class,
      icon: t.icon
    }
  })
)

// --- TRẠNG THÁI FORM TÌM KIẾM ---
const searchType = ref('all')
const searchValue = ref('')

// Trạng thái lưu trữ bộ lọc đang được CHỐT (chỉ đổi khi bấm nút "Tìm kiếm")
const appliedFilters = ref({
  type: 'all',
  value: ''
})

// Hành động khi bấm nút Tìm kiếm
const handleSearch = () => {
  appliedFilters.value = {
    type: searchType.value,
    value: searchType.value === 'TIME'
      ? searchValue.value.trim().replace(/[Tt]/g, ' ').replace(/\s+/g, ' ')
      : searchValue.value.trim()
  }
  currentPage.value = 1 
}

// Hành động khi bấm nút Làm mới
const handleReset = () => {
  searchType.value = 'all'
  searchValue.value = ''
  appliedFilters.value = { type: 'all', value: '' }
  currentPage.value = 1
}

// --- LOGIC LỌC DỮ LIỆU THỰC SỰ ---
const filteredData = computed(() => {
  return sensorHistories.value.filter(item => {
    const filters = appliedFilters.value;
    
    // TIME là chế độ tìm ngày/giờ trên tất cả cảm biến.
    if (filters.type === 'TIME') {
      const itemTime = item.time.replace(/[Tt]/g, ' ').replace(/\s+/g, ' ');
      return !filters.value || itemTime.includes(filters.value);
    }
    if (filters.type !== 'all' && item.type !== filters.type) {
      return false;
    }
    if (filters.value && !String(item.value).toLowerCase().includes(filters.value.toLowerCase())) {
      return false;
    }
    
    return true;
  })
})


const currentPage = ref(1)
const itemsPerPage = ref(8)

const handleSizeChange = () => {
  currentPage.value = 1
}

const totalPages = computed(() => Math.ceil(filteredData.value.length / itemsPerPage.value) || 1)

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  return filteredData.value.slice(start, start + itemsPerPage.value)
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
