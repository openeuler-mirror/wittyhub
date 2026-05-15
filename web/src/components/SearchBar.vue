<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')

function handleSearch() {
  if (query.value.trim()) {
    router.push({ name: 'search', query: { q: query.value.trim() } })
  }
}
</script>

<template>
  <form @submit.prevent="handleSearch" class="w-full">
    <div class="relative">
      <input
        v-model="query"
        type="text"
        placeholder="搜索 Skill..."
        class="input pl-10 pr-20 py-3 text-lg"
      />
      <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
      <button
        type="submit"
        class="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-1.5 px-4 text-sm"
      >
        搜索
      </button>
    </div>
  </form>
</template>