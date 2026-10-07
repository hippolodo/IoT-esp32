<template>
  <div class="w-84 bg-[#1a1d2e] h-screen text-gray-400 flex flex-col shrink-0 font-sans border-r border-gray-800">
    <!-- Header / Logo -->
    <div class="p-6 flex items-center space-x-3 text-white mb-4">
      <div class="w-10 h-10 bg-gray-800/50 rounded-xl flex items-center justify-center border border-gray-700">
        <i class="fa-solid fa-microchip text-xl text-blue-500"></i>
      </div>
      <div>
        <h1 class="text-base font-bold tracking-wide">SmartHome</h1>
        <p class="text-[11px] text-gray-500 font-semibold tracking-wider">AI</p>
      </div>
    </div>

    <!-- Navigation Menu -->
    <nav class="flex-1 px-4 space-y-2">
      <!-- Nút Home Dashboard -->
      <button 
        @click="$emit('change-view', 'dashboard')"
        :class="[
          'w-full flex items-center space-x-4 px-4 py-3.5 rounded-xl transition-all duration-200 group', 
          activeView === 'dashboard' 
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
            : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
        ]"
      >
        <i :class="['fa-solid fa-border-all text-lg transition-colors', activeView === 'dashboard' ? 'text-white' : 'text-gray-500 group-hover:text-gray-300']"></i>
        <span class="text-sm font-semibold">Home Dashboard</span>
      </button>

      <!-- Nút Data Sensors -->
      <button 
        @click="$emit('change-view', 'sensors')"
        :class="[
          'w-full flex items-center space-x-4 px-4 py-3.5 rounded-xl transition-all duration-200 group', 
          activeView === 'sensors' 
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
            : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
        ]"
      >
        <i :class="['fa-solid fa-server text-lg transition-colors', activeView === 'sensors' ? 'text-white' : 'text-gray-500 group-hover:text-gray-300']"></i>
        <span class="text-sm font-semibold">Data Sensors</span>
      </button>

      <!-- Nút Action History -->
      <button 
        @click="$emit('change-view', 'history')"
        :class="[
          'w-full flex items-center space-x-4 px-4 py-3.5 rounded-xl transition-all duration-200 group', 
          activeView === 'history' 
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
            : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
        ]"
      >
        <i :class="['fa-solid fa-clock-rotate-left text-lg transition-colors', activeView === 'history' ? 'text-white' : 'text-gray-500 group-hover:text-gray-300']"></i>
        <span class="text-sm font-semibold">Action History</span>
      </button>

      <!-- Nút User Profile -->
      <button 
        @click="$emit('change-view', 'profile')"
        :class="[
          'w-full flex items-center space-x-4 px-4 py-3.5 rounded-xl transition-all duration-200 group', 
          activeView === 'profile' 
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
            : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
        ]"
      >
        <i :class="['fa-regular fa-user text-lg transition-colors', activeView === 'profile' ? 'text-white' : 'text-gray-500 group-hover:text-gray-300']"></i>
        <span class="text-sm font-semibold">User Profile</span>
      </button>
    </nav>
  </div>
</template>

<script setup>
// Khai báo props nhận dữ liệu từ App.vue để biết đang ở màn hình nào
defineProps({
  activeView: {
    type: String,
    required: true,
    default: 'dashboard'
  }
})

// Khai báo emits để gửi tín hiệu lên App.vue khi user bấm đổi tab
defineEmits(['change-view'])
</script>1 free page left.