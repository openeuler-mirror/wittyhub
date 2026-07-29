import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const isDark = ref(false)
  const currentTheme = ref<'light' | 'dark'>('light')

  function initTheme() {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setTheme('dark')
    } else {
      setTheme('light')
    }
  }

  function setTheme(theme: 'light' | 'dark') {
    currentTheme.value = theme
    isDark.value = theme === 'dark'
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
      document.documentElement.setAttribute('data-o-theme', 'e.dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.documentElement.setAttribute('data-o-theme', 'e.light')
    }
    localStorage.setItem('theme', theme)
  }

  function toggleTheme() {
    setTheme(currentTheme.value === 'dark' ? 'light' : 'dark')
  }

  return {
    isDark,
    currentTheme,
    initTheme,
    setTheme,
    toggleTheme
  }
})
