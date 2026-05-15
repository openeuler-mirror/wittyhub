<script setup lang="ts">
import { RouterLink } from 'vue-router'

const categories = [
  { name: 'DevTools', icon: '🛠️', path: '/skills/categories/DevTools' },
  { name: 'AI', icon: '🤖', path: '/skills/categories/AI' },
  { name: 'Frontend', icon: '🎨', path: '/skills/categories/Frontend' },
  { name: 'Backend', icon: '⚙️', path: '/skills/categories/Backend' },
  { name: 'Cloud', icon: '☁️', path: '/skills/categories/Cloud' },
  { name: 'Testing', icon: '🧪', path: '/skills/categories/Testing' },
]
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
    <RouterLink
      v-for="cat in categories"
      :key="cat.name"
      :to="cat.path"
      class="card flex flex-col items-center justify-center p-4 hover:border-primary-200"
    >
      <span class="text-2xl mb-2">{{ cat.icon }}</span>
      <span class="text-sm font-medium text-gray-700">{{ cat.name }}</span>
    </RouterLink>
  </div>
</template>