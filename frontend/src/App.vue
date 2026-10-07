<template>
  <div class="flex h-screen bg-[#f8f9fc] font-sans overflow-hidden">
    <!-- Cột Menu bên trái -->
    <Sidebar 
      :activeView="currentView" 
      @change-view="currentView = $event" 
    />

    <!-- Cột Nội dung chính bên phải -->
    <div class="flex-1 flex flex-col h-full overflow-hidden">
      <!-- Header thanh trên cùng -->
      <header class="h-16 bg-white border-b border-gray-100 flex justify-between items-center px-8 shadow-sm shrink-0">
        <h1 class="text-lg font-bold text-gray-800">SmartHome System</h1>
        <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
          <i class="fa-solid fa-user"></i>
        </div>
      </header>

      <!-- Vùng hiển thị màn hình thay đổi linh hoạt -->
      <main class="flex-1 overflow-y-auto p-8">
        <div class="max-w-7xl mx-auto">
          <!-- <component :is="..."> sẽ tự động load Dashboard hoặc DataSensors -->
          <component :is="activeComponent" />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Sidebar from './components/Sidebar.vue'
import Dashboard from './views/Dashboard.vue'
import DataSensors from './views/DataSensors.vue'
import ActionHistory from './views/ActionHistory.vue'
import UserProfile from './views/UserProfile.vue'
// Quản lý trạng thái xem đang ở màn hình nào (mặc định là dashboard)
const currentView = ref('dashboard')

// Tự động trả về file Component tương ứng
const activeComponent = computed(() => {
  if (currentView.value === 'dashboard') return Dashboard
  if (currentView.value === 'sensors') return DataSensors
  if (currentView.value === 'history') return ActionHistory
  if (currentView.value === 'profile') return UserProfile
  return Dashboard
})
</script>