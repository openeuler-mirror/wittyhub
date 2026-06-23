<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')
const searchType = ref<'all' | 'skill' | 'agent'>('all')

function handleSearch() {
  if (query.value.trim()) {
    if (searchType.value === 'agent') {
      router.push({ name: 'agent-list', query: { q: query.value.trim() } })
    } else if (searchType.value === 'skill') {
      router.push({ name: 'search', query: { q: query.value.trim() } })
    } else {
      router.push({ name: 'search', query: { q: query.value.trim() } })
    }
  }
}
</script>

<template>
  <form @submit.prevent="handleSearch" class="w-full">
    <div class="relative">
      <div class="absolute left-3 top-1/2 -translate-y-1/2 flex gap-1">
        <button
          type="button"
          @click="searchType = 'all'"
          class="px-2 py-0.5 text-xs rounded transition-colors"
          :class="searchType === 'all' ? 'bg-white text-primary-600' : 'bg-primary-400 text-white hover:bg-primary-300'"
        >
          全部
        </button>
        <button
          type="button"
          @click="searchType = 'skill'"
          class="px-2 py-0.5 text-xs rounded transition-colors"
          :class="searchType === 'skill' ? 'bg-white text-primary-600' : 'bg-primary-400 text-white hover:bg-primary-300'"
        >
          Skills
        </button>
        <button
          type="button"
          @click="searchType = 'agent'"
          class="px-2 py-0.5 text-xs rounded transition-colors"
          :class="searchType === 'agent' ? 'bg-white text-primary-600' : 'bg-primary-400 text-white hover:bg-primary-300'"
        >
          Agents
        </button>
      </div>
      <input
        v-model="query"
        type="text"
        placeholder="搜索 Skills 和 Agents..."
        class="input pl-28 pr-24 py-3 text-lg dark:bg-gray-800 dark:border-gray-600 dark:text-white"
      />
      <button
        type="submit"
        class="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-1.5 px-4 text-sm"
      >
        搜索
      </button>
    </div>
  </form>
</template>