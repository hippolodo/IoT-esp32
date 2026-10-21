<template>
  <div
    class="w-84 bg-[#1a1d2e] h-screen text-gray-400 flex flex-col shrink-0 font-sans border-r border-gray-800"
  >
    <div class="p-6 flex items-center space-x-3 text-white mb-4">
      <div
        class="w-10 h-10 bg-gray-800/50 rounded-xl flex items-center justify-center border border-gray-700"
      >
        <i class="fa-solid fa-microchip text-xl text-blue-500"></i>
      </div>
      <div>
        <h1 class="text-base font-bold tracking-wide">SmartHome</h1>
        <p class="text-[11px] text-gray-500 font-semibold tracking-wider">AI</p>
      </div>
    </div>

    <nav class="flex-1 px-4 space-y-2">
      <button
        v-for="item in navigation"
        :key="item.view"
        @click="$emit('change-view', item.view)"
        :class="[
          'w-full flex items-center space-x-4 px-4 py-3.5 rounded-xl transition-all duration-200 group',
          activeView === item.view
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
            : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200',
        ]"
      >
        <i
          :class="[
            item.icon,
            'text-lg transition-colors',
            activeView === item.view ? 'text-white' : 'text-gray-500 group-hover:text-gray-300',
          ]"
        ></i>
        <span class="text-sm font-semibold">{{ item.label }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup>
// Khai báo props nhận dữ liệu từ App.vue để biết đang ở màn hình nào
defineProps({
  activeView: {
    type: String,
    default: 'dashboard',
  },
})

// Khai báo emits để gửi tín hiệu lên App.vue khi user bấm đổi tab
defineEmits(['change-view'])

const navigation = [
  { view: 'dashboard', label: 'Home Dashboard', icon: 'fa-solid fa-border-all' },
  { view: 'sensors', label: 'Data Sensors', icon: 'fa-solid fa-server' },
  { view: 'history', label: 'Action History', icon: 'fa-solid fa-clock-rotate-left' },
  { view: 'windAlerts', label: 'Cảnh báo tốc độ gió', icon: 'fa-solid fa-wind' },
  { view: 'profile', label: 'User Profile', icon: 'fa-regular fa-user' },
]
</script>
