<script setup lang="ts">
import { RouterLink } from 'vue-router'

const categories = [
  { name: 'Development', icon: '💻', path: '/skills/categories/Development' },
  { name: 'Marketing', icon: '📢', path: '/skills/categories/Marketing' },
  { name: 'AI', icon: '🤖', path: '/skills/categories/AI' },
  { name: 'Cloud', icon: '☁️', path: '/skills/categories/Cloud' },
  { name: 'Design', icon: '🎨', path: '/skills/categories/Design' },
  { name: 'Security', icon: '🔒', path: '/skills/categories/Security' },
]
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
    <RouterLink
      v-for="cat in categories"
      :key="cat.name"
      :to="cat.path"
      class="card flex flex-col items-center justify-center p-4 hover:border-primary-200 dark:hover:border-primary-400"
    >
      <span class="text-2xl mb-2">{{ cat.icon }}</span>
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ cat.name }}</span>
    </RouterLink>
  </div>
</template>