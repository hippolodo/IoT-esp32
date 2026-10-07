<template>
  <div class="animate-fade-in text-gray-800 font-sans pb-10">
    <!-- Header -->
    <div class="flex justify-between items-start mb-6">
      <div>
        <h2 class="text-2xl font-bold text-[#1a1d2e]">Hồ Sơ Người Dùng</h2>
        <p class="text-sm text-gray-500 mt-1">Thông tin cá nhân, liên kết dự án và thông số hệ thống IoT</p>
      </div>
      <div class="flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-full border border-blue-100">
        <span class="relative flex h-3 w-3">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
        </span>
        <span class="text-sm font-semibold text-blue-600">ESP32 Connected</span>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- CỘT TRÁI (Chiếm 4 phần) -->
      <div class="lg:col-span-4 space-y-6">
        <!-- Card 1: Avatar & Info -->
        <div class="bg-white rounded-2xl p-6 flex flex-col items-center justify-center shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100">
          <div class="w-24 h-24 rounded-full bg-gray-100 border-4 border-white shadow-md flex items-center justify-center mb-4 overflow-hidden relative">
            <i class="fa-solid fa-user text-4xl text-gray-300"></i>
            <!-- Nút đổi avatar -->
            <button class="absolute bottom-0 w-full h-1/3 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <i class="fa-solid fa-camera text-white text-xs"></i>
            </button>
          </div>
          <h3 class="text-lg font-bold text-gray-800">Nguyễn Văn Hiệp</h3>
          <p class="text-xs text-gray-500 mt-1">Lập trình viên / Quản trị viên hệ thống</p>
          
          <div class="mt-5 px-4 py-1.5 bg-green-50 rounded-full border border-green-100 flex items-center">
            <span class="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
            <span class="text-[11px] font-bold text-green-600">Tài khoản đang hoạt động</span>
          </div>
        </div>

        <!-- Card 2: Thống kê hệ thống -->
        <div class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100">
          <h4 class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-4">THỐNG KÊ HỆ THỐNG</h4>
          <div class="space-y-4">
            <div class="flex items-center p-3 bg-orange-50/50 rounded-xl border border-orange-100/50">
              <div class="w-8 h-8 rounded-full bg-orange-100 text-orange-500 flex items-center justify-center mr-3">
                <i class="fa-solid fa-plug text-sm"></i>
              </div>
              <div>
                <p class="text-sm font-bold text-gray-800">03</p>
                <p class="text-[11px] text-gray-500 font-medium">Bóng đèn kết nối</p>
              </div>
            </div>
            
            <div class="flex items-center p-3 bg-blue-50/50 rounded-xl border border-blue-100/50">
              <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-500 flex items-center justify-center mr-3">
                <i class="fa-solid fa-satellite-dish text-sm"></i>
              </div>
              <div>
                <p class="text-sm font-bold text-gray-800">03</p>
                <p class="text-[11px] text-gray-500 font-medium">Cảm biến hoạt động</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- CỘT PHẢI (Chiếm 8 phần) -->
      <div class="lg:col-span-8 space-y-6">
        
        <!-- Card 3: Thông tin cá nhân -->
        <div class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100">
          <div class="flex items-center mb-6">
            <i class="fa-regular fa-address-card text-blue-600 text-lg mr-2"></i>
            <h3 class="text-base font-bold text-gray-800">Thông Tin Cá Nhân & Liên Hệ</h3>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Họ và tên -->
            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Họ và tên</label>
              <input type="text" value="Nguyễn Văn Hiệp" class="w-full px-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" />
            </div>
            
            <!-- Username -->
            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Tên đăng nhập (Username)</label>
              <input type="text" value="admin" disabled class="w-full px-4 py-2.5 text-sm font-medium text-gray-500 bg-gray-100 border border-gray-200 rounded-lg cursor-not-allowed" />
            </div>

            <!-- Email -->
            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Email</label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
                  <i class="fa-regular fa-envelope"></i>
                </div>
                <input type="email" value="admin@gmail.com" class="w-full pl-9 pr-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" />
              </div>
            </div>

            <!-- Số điện thoại -->
            <div>
              <label class="block text-xs font-bold text-gray-500 mb-2">Số điện thoại</label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
                  <i class="fa-solid fa-phone text-xs"></i>
                </div>
                <input type="text" value="0987 654 321" class="w-full pl-9 pr-4 py-2.5 text-sm font-medium text-gray-800 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" />
              </div>
            </div>
          </div>
        </div>

        <!-- Card 4: Liên kết dự án -->
        <div class="bg-white rounded-2xl p-6 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-gray-100">
          <div class="flex items-center mb-6">
            <i class="fa-solid fa-link text-blue-600 text-lg mr-2"></i>
            <h3 class="text-base font-bold text-gray-800">Liên Kết Dự Án & Tài Nguyên</h3>
          </div>

          <div class="space-y-4">
            <!-- Github Link -->
            <div class="flex items-center space-x-3">
              <div class="relative flex-1">
                <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
                  <i class="fa-solid fa-code"></i>
                </div>
                <input type="text" value="https://github.com/hippolodo/IoT-esp32" readonly class="w-full pl-9 pr-4 py-2.5 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg outline-none" />
              </div>
              <button class="px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors flex items-center shrink-0">
                Github
              </button>
            </div>

            <!-- Figma Link -->
            <div class="flex items-center space-x-3">
              <div class="relative flex-1">
                <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
                  <i class="fa-brands fa-figma"></i>
                </div>
                <input type="text" value="https://www.figma.com/design/ldQydGxj6oVYl7TOKpCjx7/IOT?node-id=0-1&t=gkSAMCVuBALT2IE8-0" readonly class="w-full pl-9 pr-4 py-2.5 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg outline-none" />
              </div>
              <button class="px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors flex items-center shrink-0">
                Xem thiết kế
              </button>
            </div>

            <div class="flex items-center space-x-3">
              <div class="relative flex-1">
                <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
                  <i class="fa-brands fa-figma"></i>
                </div>
                <input type="text" value="https://www.figma.com/design/ldQydGxj6oVYl7TOKpCjx7/IOT?node-id=0-1&t=gkSAMCVuBALT2IE8-0" readonly class="w-full pl-9 pr-4 py-2.5 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg outline-none" />
              </div>
              <button class="px-4 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold rounded-lg transition-colors flex items-center shrink-0">
                PostMan
              </button>
            </div>
          </div>
        </div>

        <!-- Buttons Hành động -->
        <div class="flex justify-end items-center space-x-3 pt-2">
          <button class="px-5 py-2.5 text-sm font-semibold text-gray-500 hover:text-gray-700 transition-colors">
            Hủy bỏ
          </button>
          <button class="px-5 py-2.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-semibold rounded-lg transition-colors shadow-sm">
            Đổi mật khẩu
          </button>
          <button class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm shadow-blue-500/30">
            Lưu thay đổi
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
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