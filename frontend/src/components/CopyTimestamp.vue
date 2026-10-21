<template>
  <span class="inline-flex items-center gap-1.5">
    <button
      type="button"
      :title="`Sao chép thời gian: ${text}`"
      :aria-label="`Sao chép thời gian: ${text}`"
      :disabled="copying"
      class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-blue-50 hover:text-blue-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:opacity-50"
      @click="copy"
    >
      <i
        :class="copied ? 'fa-solid fa-check text-emerald-600' : 'fa-regular fa-copy'"
        aria-hidden="true"
      ></i>
    </button>
    <span
      role="status"
      :class="['text-xs', copied ? 'text-emerald-600' : 'text-red-600']"
    >{{ message }}</span>
  </span>
</template>

<script setup>
import { onUnmounted, ref } from 'vue'

const props = defineProps({ text: { type: String, required: true } })
const copying = ref(false)
const copied = ref(false)
const message = ref('')
let resetTimer

// Hỗ trợ cả trang HTTP trong mạng LAN khi Clipboard API không khả dụng.
function copyWithSelection(text) {
  const previousFocus = document.activeElement
  const field = document.createElement('textarea')
  field.value = text
  field.readOnly = true
  field.style.position = 'fixed'
  field.style.opacity = '0'
  document.body.appendChild(field)
  try {
    field.select()
    if (!document.execCommand('copy')) throw new Error('Copy failed')
  } finally {
    field.remove()
    previousFocus?.focus({ preventScroll: true })
  }
}

async function copy() {
  if (copying.value) return
  clearTimeout(resetTimer)
  copying.value = true
  copied.value = false
  message.value = ''
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(props.text)
    } else {
      copyWithSelection(props.text)
    }
    copied.value = true
    message.value = 'Đã sao chép'
  } catch {
    message.value = 'Không thể sao chép'
  } finally {
    copying.value = false
    resetTimer = setTimeout(() => {
      copied.value = false
      message.value = ''
    }, 2500)
  }
}

onUnmounted(() => clearTimeout(resetTimer))
</script>
