<template>
  <div v-if="!user" class="min-h-screen bg-[#f8f9fc] flex items-center justify-center p-6">
    <form class="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm space-y-5" @submit.prevent="login">
      <h1 class="text-xl font-bold text-gray-800">Đăng nhập SmartHome</h1>
      <p v-if="authError" role="alert" class="text-sm text-red-600">{{ authError }}</p>
      <label class="block text-sm font-medium text-gray-700">Tên đăng nhập
        <input v-model="username" autocomplete="username" required class="mt-2 w-full rounded-lg border border-gray-300 p-3" />
      </label>
      <label class="block text-sm font-medium text-gray-700">Mật khẩu
        <input v-model="password" type="password" autocomplete="current-password" required class="mt-2 w-full rounded-lg border border-gray-300 p-3" />
      </label>
      <button :disabled="authBusy" class="w-full rounded-lg bg-blue-600 p-3 font-semibold text-white disabled:opacity-50">{{ authBusy ? 'Đang xử lý…' : 'Đăng nhập' }}</button>
    </form>
  </div>
  <div v-else class="flex h-screen bg-[#f8f9fc] font-sans overflow-hidden">
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
        <div class="flex items-center gap-4 text-sm">
          <span>{{ user.fullName || user.username }}</span>
          <button @click="logout" :disabled="authBusy" class="text-blue-600 disabled:opacity-50">Đăng xuất</button>
        </div>
      </header>

      <!-- Vùng hiển thị màn hình thay đổi linh hoạt -->
      <main class="flex-1 overflow-y-auto p-8">
        <p v-if="system.error" role="alert" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ system.error }}</p>
        <div class="max-w-7xl mx-auto">
          <!-- <component :is="..."> sẽ tự động load Dashboard hoặc DataSensors -->
          <component :is="activeComponent" />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { startSystem, stopSystem, system } from './services/system'
import { api, setAccessToken } from './services/api'
const user = ref(null)
const username = ref('')
const password = ref('')
const authError = ref('')
const authBusy = ref(false)

function clearSession() {
  stopSystem()
  setAccessToken('')
  user.value = null
  Object.assign(system, { devices: [], sensors: {}, points: [], error: '', sensorError: '', controlError: '', sending: {} })
}
function sessionExpired() {
  clearSession()
  authError.value = 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
}
async function login() {
  authBusy.value = true
  authError.value = ''
  try {
    const result = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username: username.value, password: password.value }) })
    setAccessToken(result.accessToken)
    user.value = result
    password.value = ''
    currentView.value = 'dashboard'
    startSystem()
  } catch (error) { authError.value = error.message }
  finally { authBusy.value = false }
}
async function logout() {
  authBusy.value = true
  try {
    await api('/api/auth/logout', { method: 'POST' })
    clearSession()
  } catch (error) { system.error = error.message }
  finally { authBusy.value = false }
}
onMounted(async () => {
  window.addEventListener('auth-expired', sessionExpired)
  if (!sessionStorage.getItem('accessToken')) return
  try {
    user.value = await api('/api/user/profile')
    startSystem()
  } catch (error) { clearSession(); authError.value = error.message }
})
onUnmounted(() => {
  window.removeEventListener('auth-expired', sessionExpired)
  stopSystem()
})
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
