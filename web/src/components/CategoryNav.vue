<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'

const categories = ref<{ name: string; count: number }[]>([])
const loading = ref(true)

const categoryIcons: Record<string, string> = {
  'Development': '💻',
  'development': '💻',
  'Marketing': '📢',
  'marketing': '📢',
  'AI': '🤖',
  'ai': '🤖',
  'Cloud': '☁️',
  'cloud': '☁️',
  'Design': '🎨',
  'design': '🎨',
  'Security': '🔒',
  'security': '🔒',
  'utility': '🔧',
  'data': '📊',
  'developer-tools': '🛠️',
}

async function loadCategories() {
  try {
    const res = await api.getCategories()
    categories.value = res.categories
  } catch (e) {
    console.error('Failed to load categories:', e)
  } finally {
    loading.value = false
  }
}

function getIcon(name: string): string {
  return categoryIcons[name] || '📁'
}

onMounted(() => {
  loadCategories()
})
</script>

<template>
  <div v-if="loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
    <div v-for="i in 6" :key="i" class="card flex flex-col items-center justify-center p-4 animate-pulse">
      <div class="h-8 w-8 bg-gray-200 rounded mb-2 dark:bg-gray-700"></div>
      <div class="h-4 w-16 bg-gray-200 rounded dark:bg-gray-700"></div>
    </div>
  </div>
  <div v-else-if="categories.length === 0" class="text-center text-gray-500 py-8">
    暂无分类
  </div>
  <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
    <RouterLink
      v-for="cat in categories"
      :key="cat.name"
      :to="`/skills/search?category=${encodeURIComponent(cat.name)}`"
      class="card flex flex-col items-center justify-center p-4 hover:border-primary-200 dark:hover:border-primary-400"
    >
      <span class="text-2xl mb-2">{{ getIcon(cat.name) }}</span>
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ cat.name }}</span>
      <span class="text-xs text-gray-400 dark:text-gray-500">{{ cat.count }}</span>
    </RouterLink>
  </div>
</template>