<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AgentCard from '@/components/AgentCard.vue'
import { api } from '@/api/client'
import type { Agent } from '@/api/types'

const route = useRoute()
const router = useRouter()

const agents = ref<Agent[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const selectedCategory = ref('')
const selectedSecurity = ref('')
const query = ref('')
const skip = ref(0)
const limit = 50
const hasMore = ref(true)
let observer: IntersectionObserver | null = null
const loadMoreTrigger = ref<HTMLElement | null>(null)

const securityLevels = [
  { label: '高安全 (90+)', value: 'high', min: 90 },
  { label: '中安全 (80-89)', value: 'medium', min: 80 },
  { label: '低安全 (70-79)', value: 'low', min: 70 },
]

const filteredAgents = computed(() => {
  let result = agents.value

  // Filter by search query
  if (query.value.trim()) {
    const q = query.value.toLowerCase()
    result = result.filter(a =>
      a.name.toLowerCase().includes(q) ||
      a.description?.toLowerCase().includes(q) ||
      a.tags?.some(t => t.toLowerCase().includes(q)) ||
      a.category?.toLowerCase().includes(q)
    )
  }

  // Filter by security level
  if (selectedSecurity.value) {
    const secLevel = securityLevels.find(s => s.value === selectedSecurity.value)
    if (secLevel) {
      result = result.filter(a => a.security_score !== null && a.security_score >= secLevel.min)
    }
  }

  return result
})

const computedCategories = computed(() => {
  const catMap = new Map<string, number>()
  agents.value.forEach(a => {
    if (a.category) {
      catMap.set(a.category, (catMap.get(a.category) || 0) + 1)
    }
  })
  return Array.from(catMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})

async function fetchAgents(reset = true) {
  if (reset) {
    loading.value = true
    skip.value = 0
    hasMore.value = true
  } else {
    loadingMore.value = true
  }

  try {
    const res = await api.listAgents({
      skip: skip.value,
      limit: limit,
    })
    if (reset) {
      agents.value = res.agents
    } else {
      agents.value = [...agents.value, ...res.agents]
    }
    total.value = res.total
    hasMore.value = agents.value.length < res.total
    skip.value += res.agents.length
  } catch (e) {
    console.error('Fetch failed:', e)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  await fetchAgents(false)
}

function selectCategory(cat: string) {
  selectedCategory.value = selectedCategory.value === cat ? '' : cat
  fetchAgents()
}

function selectSecurity(level: string) {
  selectedSecurity.value = selectedSecurity.value === level ? '' : level
}

function handleSearch() {
  router.push({ name: 'agent-list', query: { q: query.value || undefined } })
}

function setupObserver() {
  if (observer) observer.disconnect()

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loadingMore.value) {
        loadMore()
      }
    },
    { threshold: 0.1 }
  )

  if (loadMoreTrigger.value) {
    observer.observe(loadMoreTrigger.value)
  }
}

watch(loadMoreTrigger, () => {
  setupObserver()
})

watch(() => route.query, (q) => {
  query.value = (q.q as string) || ''
}, { immediate: true })

onMounted(async () => {
  query.value = (route.query.q as string) || ''
  fetchAgents()
  setupObserver()
})

onUnmounted(() => {
  if (observer) observer.disconnect()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Agents</h1>
      <p class="text-gray-500 dark:text-gray-400">Browse and discover AI agents for your workflow</p>
    </div>

    <!-- Search -->
    <form @submit.prevent="handleSearch" class="mb-6">
      <div class="flex gap-2">
        <input
          v-model="query"
          type="text"
          placeholder="Search agents..."
          class="input flex-1"
        />
        <button type="submit" class="btn-primary">搜索</button>
      </div>
    </form>

    <!-- Categories -->
    <div class="mb-4">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">分类</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="cat in computedCategories"
          :key="cat.name"
          @click="selectCategory(cat.name)"
          class="px-3 py-1.5 text-sm rounded-full transition-colors"
          :class="selectedCategory === cat.name
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'"
        >
          {{ cat.name }} ({{ cat.count }})
        </button>
      </div>
    </div>

    <!-- Security Levels -->
    <div class="mb-6">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">安全等级</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="sec in securityLevels"
          :key="sec.value"
          @click="selectSecurity(sec.value)"
          class="px-3 py-1.5 text-sm rounded-full transition-colors"
          :class="selectedSecurity === sec.value
            ? 'bg-green-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'"
        >
          {{ sec.label }}
        </button>
      </div>
    </div>

    <div class="mb-4">
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {{ filteredAgents.length.toLocaleString() }} agents
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 9" :key="i" class="card animate-pulse">
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-gray-100 dark:bg-gray-600 rounded w-1/2 mb-4"></div>
        <div class="h-16 bg-gray-100 dark:bg-gray-600 rounded"></div>
      </div>
    </div>

    <div v-else-if="filteredAgents.length === 0" class="text-center py-16">
      <p class="text-gray-500 dark:text-gray-400">No agents found</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <AgentCard v-for="agent in filteredAgents" :key="agent.id" :agent="agent" />
    </div>

    <div ref="loadMoreTrigger" class="h-10 flex items-center justify-center mt-6">
      <div v-if="loadingMore" class="animate-pulse text-gray-500 dark:text-gray-400">
        Loading more...
      </div>
      <div v-else-if="!hasMore" class="text-gray-400 dark:text-gray-500">
        No more agents
      </div>
    </div>
  </div>
</template>
