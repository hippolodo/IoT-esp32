<template>
  <div class="animate-fade-in text-gray-800 font-sans">
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-[#1a1d2e]">Lịch Sử Dữ Liệu Cảm Biến</h2>
      <p class="text-sm text-gray-500 mt-1">
        Tra cứu thông số đo nhiệt độ, độ ẩm và ánh sáng từ cơ sở dữ liệu
      </p>
    </div>

    <div
      class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 mb-6"
    >
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-5">
        <div>
          <label class="block text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide"
            >Loại Cảm Biến</label
          >
          <div class="relative">
            <select
              v-model="searchType"
              class="block w-full pl-4 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white"
            >
              <option value="all">Tất cả cảm biến</option>
              <option value="TEMPERATURE">Nhiệt độ (Temperature)</option>
              <option value="HUMIDITY">Độ ẩm (Humidity)</option>
              <option value="LIGHT">Ánh sáng (Light)</option>
              <option value="WIND_SPEED">Tốc độ gió (Wind Speed)</option>
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
              :placeholder="
                searchType === 'TIME' ? 'VD: 2026-10-18 hoặc 2026-10-18 17:30' : 'VD: 28.4, 66, 400...'
              "
              class="block w-full pl-9 pr-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 bg-white transition-colors"
            />
          </div>
        </div>
      </div>

      <div class="flex space-x-3">
        <button
          @click="handleSearch"
          class="flex items-center px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm shadow-blue-500/30"
        >
          <i class="fa-solid fa-magnifying-glass mr-2 text-xs"></i> Tìm kiếm
        </button>
        <button
          @click="handleReset"
          class="flex items-center px-5 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg transition-colors shadow-sm"
        >
          <i class="fa-solid fa-rotate-right mr-2 text-xs"></i> Làm mới
        </button>
      </div>
    </div>

    <p v-if="error" role="alert" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <p v-if="loading" role="status" class="mb-3 text-sm text-gray-500">Đang tải dữ liệu…</p>
    <div
      class="bg-white rounded-2xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100 overflow-hidden"
    >
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 border-b border-gray-200">
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-20">#ID</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Tên Cảm Biến</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">
                Loại Cảm Biến
              </th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Giá Trị Đo</th>
              <th class="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">
                Thời Gian Ghi Nhận
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="!loading && !paginatedData.length">
              <td colspan="5" class="p-8 text-center text-sm text-gray-500">Không có dữ liệu phù hợp.</td>
            </tr>
            <tr v-for="item in paginatedData" :key="item.id" class="hover:bg-blue-50/30 transition-colors">
              <td class="px-6 py-4 text-sm text-gray-500">{{ item.id }}</td>
              <td class="px-6 py-4 text-sm font-semibold text-gray-800">{{ item.name }}</td>
              <td class="px-6 py-4">
                <span
                  :class="[
                    'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border',
                    item.typeClass,
                  ]"
                >
                  <i :class="['fa-solid mr-1.5', item.icon]"></i> {{ item.type }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm font-bold text-gray-800">{{ item.value }}</td>
              <td class="px-6 py-4 text-sm text-gray-500">
                <div class="flex items-center gap-2">
                  <span class="whitespace-nowrap">{{ item.time }}</span>
                  <CopyTimestamp :text="item.time" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex items-center justify-between">
        <div class="flex items-center space-x-6">
          <span class="text-[11px] font-semibold text-gray-400">
            Hiển thị trang {{ total === 0 ? 0 : currentPage }} / {{ totalPages }} (Tổng {{ total }} bản ghi)
          </span>

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

        <div class="flex space-x-1">
          <button
            @click="prevPage"
            :disabled="currentPage <= 1 || loading"
            class="px-2 py-1 text-xs font-semibold text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            Trước
          </button>

          <button
            v-for="page in visiblePages"
            :key="page"
            @click="goToPage(page)"
            :class="[
              'w-7 h-7 flex items-center justify-center text-xs rounded-md transition-colors',
              currentPage === page
                ? 'font-bold bg-blue-600 text-white shadow-sm'
                : 'font-bold text-gray-500 hover:bg-gray-100',
            ]"
          >
            {{ page }}
          </button>

          <button
            @click="nextPage"
            :disabled="currentPage >= totalPages || loading"
            class="px-2 py-1 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors disabled:opacity-50"
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import CopyTimestamp from '../components/CopyTimestamp.vue'
import { usePage } from '../composables/usePage'
const searchType = ref('all'),
  searchValue = ref('')
const applied = ref({ type: 'all', value: '' })
const {
  rows,
  currentPage,
  itemsPerPage,
  total,
  totalPages,
  visiblePages,
  loading,
  error,
  load,
  handleSizeChange,
  goToPage,
  nextPage,
  prevPage,
} = usePage(
  '/api/sensors/data',
  () => {
    const { type, value } = applied.value
    return {
      sensorType: ['all', 'TIME'].includes(type) ? undefined : type,
      value: type !== 'TIME' ? value : undefined,
      startTime: type === 'TIME' && value ? value : undefined,
      endTime: type === 'TIME' && value ? value : undefined,
    }
  },
  '/topic/sensors',
)
const styles = {
  TEMPERATURE: ['fa-temperature-half', 'bg-red-100 text-red-600 border-red-200/50'],
  HUMIDITY: ['fa-droplet', 'bg-blue-100 text-blue-600 border-blue-200/50'],
  LIGHT: ['fa-sun', 'bg-indigo-100 text-indigo-600 border-indigo-200/50'],
  WIND_SPEED: ['fa-wind', 'bg-cyan-100 text-cyan-700 border-cyan-200/50'],
}
const paginatedData = computed(() =>
  rows.value.map((row) => {
    const type = row.sensorType.toUpperCase()
    const [icon, typeClass] = styles[type] || ['fa-gauge', 'bg-gray-100 text-gray-600']
    return {
      id: row.id,
      name: row.sensorName,
      type,
      icon,
      typeClass,
      value: `${row.value} ${type === 'LIGHT' ? 'ADC' : row.unit}`,
      time: row.recordedAt,
    }
  }),
)
const handleSearch = () => {
  applied.value = {
    type: searchType.value,
    value: searchValue.value.trim().replace(/[Tt]/g, ' ').replace(/\s+/g, ' '),
  }
  currentPage.value = 1
  load()
}
const handleReset = () => {
  searchType.value = 'all'
  searchValue.value = ''
  handleSearch()
}
</script>
