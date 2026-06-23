<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ref, onMounted } from 'vue'

const isDark = ref(false)

function toggleDark() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('darkMode', 'true')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('darkMode', 'false')
  }
}

onMounted(() => {
  const saved = localStorage.getItem('darkMode')
  if (saved === 'true' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
})
</script>

<template>
  <header class="bg-white border-b border-gray-100 sticky top-0 z-50 dark:bg-gray-800 dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <RouterLink to="/" class="flex items-center gap-2">
          <div class="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <span class="text-white font-bold text-sm">W</span>
          </div>
          <span class="text-xl font-semibold text-primary-500">wittyhub</span>
        </RouterLink>

        <nav class="hidden md:flex items-center gap-6">
          <RouterLink to="/" class="text-gray-600 hover:text-primary-500 transition-colors dark:text-gray-300">首页</RouterLink>
          <RouterLink to="/agents/" class="text-gray-600 hover:text-primary-500 transition-colors dark:text-gray-300">Agents</RouterLink>
          <RouterLink to="/skills/search" class="text-gray-600 hover:text-primary-500 transition-colors dark:text-gray-300">Skills</RouterLink>
          <RouterLink to="/leaderboard" class="text-gray-600 hover:text-primary-500 transition-colors dark:text-gray-300">排行榜</RouterLink>
        </nav>

        <div class="flex items-center gap-4">
          <button
            @click="toggleDark"
            class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
          >
            <svg v-if="isDark" class="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
            </svg>
            <svg v-else class="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
            </svg>
          </button>
          <RouterLink
            to="/skills/search"
            class="btn-primary text-sm"
          >
            搜索
          </RouterLink>
        </div>
      </div>
    </div>
  </header>
</template>