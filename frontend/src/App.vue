<template>
  <div v-if="!user" class="min-h-screen bg-[#f8f9fc] flex items-center justify-center p-6">
    <form class="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm space-y-5" @submit.prevent="submitAuth">
      <h1 class="text-xl font-bold text-gray-800">
        {{ isRegistering ? 'Đăng ký tài khoản' : 'Đăng nhập SmartHome' }}
      </h1>
      <p v-if="authError" role="alert" class="text-sm text-red-600">{{ authError }}</p>
      <p v-if="authSuccess" role="status" class="text-sm text-green-700">{{ authSuccess }}</p>
      <label class="block text-sm font-medium text-gray-700"
        >Tên đăng nhập
        <input
          v-model="username"
          autocomplete="username"
          :minlength="isRegistering ? 3 : undefined"
          :maxlength="isRegistering ? 50 : undefined"
          :pattern="isRegistering ? '[A-Za-z0-9_.-]{3,50}' : undefined"
          :title="isRegistering ? '3–50 ký tự: chữ, số, dấu chấm, gạch dưới hoặc gạch ngang' : undefined"
          required
          class="mt-2 w-full rounded-lg border border-gray-300 p-3"
        />
      </label>
      <label v-if="isRegistering" class="block text-sm font-medium text-gray-700"
        >Họ và tên
        <input
          v-model="fullName"
          autocomplete="name"
          maxlength="255"
          required
          class="mt-2 w-full rounded-lg border border-gray-300 p-3"
        />
      </label>
      <label v-if="isRegistering" class="block text-sm font-medium text-gray-700"
        >Email
        <input
          v-model="email"
          type="email"
          autocomplete="email"
          maxlength="255"
          required
          class="mt-2 w-full rounded-lg border border-gray-300 p-3"
        />
      </label>
      <label class="block text-sm font-medium text-gray-700"
        >Mật khẩu
        <input
          v-model="password"
          type="password"
          :autocomplete="isRegistering ? 'new-password' : 'current-password'"
          :minlength="isRegistering ? 8 : undefined"
          :maxlength="isRegistering ? 128 : undefined"
          required
          class="mt-2 w-full rounded-lg border border-gray-300 p-3"
        />
      </label>
      <p v-if="isRegistering" class="text-xs text-gray-500">Mật khẩu từ 8 đến 128 ký tự.</p>
      <label v-if="isRegistering" class="block text-sm font-medium text-gray-700"
        >Xác nhận mật khẩu
        <input
          v-model="confirmPassword"
          type="password"
          autocomplete="new-password"
          maxlength="128"
          required
          class="mt-2 w-full rounded-lg border border-gray-300 p-3"
        />
      </label>
      <button
        :disabled="authBusy"
        class="w-full rounded-lg bg-blue-600 p-3 font-semibold text-white disabled:opacity-50"
      >
        {{ authBusy ? 'Đang xử lý…' : isRegistering ? 'Đăng ký' : 'Đăng nhập' }}
      </button>
      <button
        type="button"
        :disabled="authBusy"
        @click="switchAuthMode"
        class="w-full text-sm text-blue-600 disabled:opacity-50"
      >
        {{ isRegistering ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký' }}
      </button>
    </form>
  </div>
  <div v-else class="flex h-screen bg-[#f8f9fc] font-sans overflow-hidden">
    <Sidebar :activeView="currentView" @change-view="currentView = $event" />

    <div class="flex-1 flex flex-col h-full overflow-hidden">
      <header
        class="h-16 bg-white border-b border-gray-100 flex justify-between items-center px-8 shadow-sm shrink-0"
      >
        <h1 class="text-lg font-bold text-gray-800">SmartHome System</h1>
        <div class="flex items-center gap-4 text-sm">
          <span>{{ user.fullName || user.username }}</span>
          <button @click="logout" :disabled="authBusy" class="text-blue-600 disabled:opacity-50">
            Đăng xuất
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-8">
        <p v-if="system.error" role="alert" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {{ system.error }}
        </p>
        <div class="max-w-7xl mx-auto">
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
import Sidebar from './components/Sidebar.vue'
import Dashboard from './views/Dashboard.vue'
import DataSensors from './views/DataSensors.vue'
import ActionHistory from './views/ActionHistory.vue'
import UserProfile from './views/UserProfile.vue'

const views = {
  dashboard: Dashboard,
  sensors: DataSensors,
  history: ActionHistory,
  profile: UserProfile,
}
const currentView = ref('dashboard')
const activeComponent = computed(() => views[currentView.value] || Dashboard)
const user = ref(null)
const username = ref('')
const password = ref('')
const fullName = ref('')
const email = ref('')
const confirmPassword = ref('')
const isRegistering = ref(false)
const authError = ref('')
const authSuccess = ref('')
const authBusy = ref(false)

function clearSession() {
  stopSystem()
  setAccessToken('')
  user.value = null
  Object.assign(system, {
    devices: [],
    sensors: {},
    points: [],
    error: '',
    sensorError: '',
    controlError: '',
    sending: {},
  })
}
function sessionExpired() {
  clearSession()
  authError.value = 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
}
function switchAuthMode() {
  isRegistering.value = !isRegistering.value
  password.value = ''
  confirmPassword.value = ''
  authError.value = ''
  authSuccess.value = ''
}
async function submitAuth() {
  if (authBusy.value) return
  if (!isRegistering.value) return login()
  authError.value = ''
  authSuccess.value = ''
  if (password.value !== confirmPassword.value) {
    authError.value = 'Xác nhận mật khẩu không khớp'
    return
  }
  authBusy.value = true
  try {
    const result = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: username.value,
        fullName: fullName.value,
        email: email.value,
        password: password.value,
        confirmPassword: confirmPassword.value,
      }),
    })
    username.value = result.username
    password.value = ''
    confirmPassword.value = ''
    fullName.value = ''
    email.value = ''
    isRegistering.value = false
    authSuccess.value = 'Đăng ký thành công. Bạn hãy đăng nhập bằng tài khoản vừa tạo.'
  } catch (error) {
    authError.value = error.message
  } finally {
    authBusy.value = false
  }
}
async function login() {
  authBusy.value = true
  authError.value = ''
  authSuccess.value = ''
  try {
    const result = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    setAccessToken(result.accessToken)
    user.value = result
    password.value = ''
    currentView.value = 'dashboard'
    startSystem()
  } catch (error) {
    authError.value = error.message
  } finally {
    authBusy.value = false
  }
}
async function logout() {
  authBusy.value = true
  try {
    await api('/api/auth/logout', { method: 'POST' })
    clearSession()
  } catch (error) {
    system.error = error.message
  } finally {
    authBusy.value = false
  }
}
onMounted(async () => {
  window.addEventListener('auth-expired', sessionExpired)
  if (!sessionStorage.getItem('accessToken')) return
  try {
    user.value = await api('/api/user/profile')
    startSystem()
  } catch (error) {
    clearSession()
    authError.value = error.message
  }
})
onUnmounted(() => {
  window.removeEventListener('auth-expired', sessionExpired)
  stopSystem()
})
</script>
