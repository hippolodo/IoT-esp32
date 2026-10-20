<template>
  <div class="animate-fade-in text-gray-800 font-sans pb-10">
    <div class="flex justify-between items-start mb-6">
      <div>
        <h2 class="text-2xl font-bold text-[#1a1d2e]">Hồ Sơ Người Dùng</h2>
        <p class="text-sm text-gray-500 mt-1">Thông tin cá nhân, liên kết dự án và thông số hệ thống IoT</p>
      </div>
      <ConnectionStatus />
    </div>

    <p v-if="error" role="alert" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <p v-if="loading" role="status" class="mb-3 text-sm text-gray-500">Đang tải hồ sơ…</p>
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div class="lg:col-span-4 space-y-6">
        <div
          class="bg-white rounded-2xl p-6 flex flex-col items-center justify-center shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100"
        >
          <div
            class="w-24 h-24 rounded-full bg-gray-100 border-4 border-white shadow-md flex items-center justify-center mb-4 overflow-hidden relative"
          >
            <i class="fa-solid fa-user text-4xl text-gray-300"></i>
            <button
              disabled
              aria-label="Đổi ảnh chưa khả dụng"
              class="absolute bottom-0 w-full h-1/3 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
            >
              <i class="fa-solid fa-camera text-white text-xs"></i>
            </button>
          </div>
          <h3 class="text-lg font-bold text-gray-800">{{ profile?.fullName || '—' }}</h3>
          <p class="text-xs text-gray-500 mt-1">Lập trình viên / Quản trị viên hệ thống</p>

          <div class="mt-5 px-4 py-1.5 bg-green-50 rounded-full border border-green-100 flex items-center">
            <span class="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
            <span class="text-[11px] font-bold text-green-600">Hồ sơ quản trị viên</span>
          </div>
        </div>

        <div
          class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100"
        >
          <h4 class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-4">THỐNG KÊ HỆ THỐNG</h4>
          <div class="space-y-4">
            <div class="flex items-center p-3 bg-orange-50/50 rounded-xl border border-orange-100/50">
              <div
                class="w-8 h-8 rounded-full bg-orange-100 text-orange-500 flex items-center justify-center mr-3"
              >
                <i class="fa-solid fa-plug text-sm"></i>
              </div>
              <div>
                <p class="text-sm font-bold text-gray-800">
                  {{ system.devices.filter((device) => device.controllable).length }}
                </p>
                <p class="text-[11px] text-gray-500 font-medium">Đèn đã cấu hình</p>
              </div>
            </div>

            <div class="flex items-center p-3 bg-blue-50/50 rounded-xl border border-blue-100/50">
              <div
                class="w-8 h-8 rounded-full bg-blue-100 text-blue-500 flex items-center justify-center mr-3"
              >
                <i class="fa-solid fa-satellite-dish text-sm"></i>
              </div>
              <div>
                <p class="text-sm font-bold text-gray-800">{{ sensorCount }}</p>
                <p class="text-[11px] text-gray-500 font-medium">Cảm biến đã đăng ký</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="lg:col-span-8 space-y-6">
        <div
          class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100"
        >
          <div class="flex items-center mb-6">
            <i class="fa-regular fa-address-card text-blue-600 text-lg mr-2"></i>
            <h3 class="text-base font-bold text-gray-800">Thông Tin Cá Nhân & Liên Hệ</h3>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Họ và tên</label>
              <input
                type="text"
                :value="profile?.fullName || ''"
                readonly
                class="w-full px-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-50 border border-gray-200 rounded-lg outline-none"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Tên đăng nhập (Username)</label>
              <input
                type="text"
                :value="profile?.username || ''"
                disabled
                class="w-full px-4 py-2.5 text-sm font-medium text-gray-500 bg-gray-100 border border-gray-200 rounded-lg cursor-not-allowed"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Email</label>
              <div class="relative">
                <div
                  class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400"
                >
                  <i class="fa-regular fa-envelope"></i>
                </div>
                <input
                  type="email"
                  :value="profile?.email || ''"
                  readonly
                  class="w-full pl-9 pr-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Số điện thoại</label>
              <div class="relative">
                <div
                  class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400"
                >
                  <i class="fa-solid fa-phone text-xs"></i>
                </div>
                <input
                  type="text"
                  value=""
                  placeholder="Chưa có thông tin"
                  readonly
                  class="w-full pl-9 pr-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-50 border border-gray-200 rounded-lg outline-none"
                />
              </div>
            </div>
          </div>
        </div>

        <div
          class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100"
        >
          <div class="flex items-center mb-6">
            <i class="fa-solid fa-link text-blue-600 text-lg mr-2"></i>
            <h3 class="text-base font-bold text-gray-800">Liên Kết</h3>
          </div>

          <div class="space-y-4">
            <div class="flex items-center space-x-3">
              <div class="relative flex-1">
                <div
                  class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400"
                >
                  <i class="fa-solid fa-code"></i>
                </div>
                <input
                  type="text"
                  value="https://github.com/hippolodo/IoT-esp32"
                  readonly
                  class="w-full pl-9 pr-4 py-2.5 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg outline-none"
                />
              </div>
              <button
                class="px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors flex items-center shrink-0"
              >
                Github
              </button>
            </div>

            <div class="flex items-center space-x-3">
              <div class="relative flex-1">
                <div
                  class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400"
                >
                  <i class="fa-brands fa-figma"></i>
                </div>
                <input
                  type="text"
                  value="https://www.figma.com/design/ldQydGxj6oVYl7TOKpCjx7/IOT?node-id=0-1&t=gkSAMCVuBALT2IE8-0"
                  readonly
                  class="w-full pl-9 pr-4 py-2.5 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg outline-none"
                />
              </div>
              <button
                class="px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors flex items-center shrink-0"
              >
                Xem thiết kế
              </button>
            </div>

            <div class="flex items-center space-x-3">
              <div class="relative flex-1">
                <div
                  class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400"
                >
                  <i class="fa-brands fa-figma"></i>
                </div>
                <input
                  type="text"
                  value="https://www.figma.com/design/ldQydGxj6oVYl7TOKpCjx7/IOT?node-id=0-1&t=gkSAMCVuBALT2IE8-0"
                  readonly
                  class="w-full pl-9 pr-4 py-2.5 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg outline-none"
                />
              </div>
              <button
                class="px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors flex items-center shrink-0"
              >
                PostMan
              </button>
            </div>
          </div>
        </div>

        <p class="text-sm text-gray-500">Hồ sơ hiện ở chế độ xem.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import { system } from '../services/system'
import { api } from '../services/api'
const profile = ref(null),
  sensorCount = ref(0),
  loading = ref(true),
  error = ref('')
const controller = new AbortController()
onMounted(async () => {
  try {
    const [user, sensors] = await Promise.all([
      api('/api/user/profile', { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]) }),
      api('/api/sensors', { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]) }),
    ])
    profile.value = user
    sensorCount.value = sensors.length
  } catch (err) {
    if (err.name !== 'AbortError') error.value = err.message
  } finally {
    loading.value = false
  }
})
onUnmounted(() => controller.abort())
</script>
