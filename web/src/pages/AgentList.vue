<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import AgentCard from '@/components/AgentCard.vue'
import { api } from '@/api/client'
import type { Agent } from '@/api/types'

const route = useRoute()

const agents = ref<Agent[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const selectedCategory = ref('')
const selectedSecurity = ref('')
const skip = ref(0)
const limit = 50
const hasMore = ref(true)
let observer: IntersectionObserver | null = null
const loadMoreTrigger = ref<HTMLElement | null>(null)

const categories = ref<{ name: string; count: number }[]>([])
const securityLevels = [
  { label: '高安全 (90+)', value: 'high', min: 90 },
  { label: '中安全 (80-89)', value: 'medium', min: 80 },
  { label: '低安全 (70-79)', value: 'low', min: 70 },
]

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
      category: selectedCategory.value || undefined,
    })
    let results = res.agents
    if (selectedSecurity.value) {
      const secLevel = securityLevels.find(s => s.value === selectedSecurity.value)
      if (secLevel) {
        results = results.filter(a => a.security_score !== null && a.security_score >= secLevel.min)
      }
    }
    if (reset) {
      agents.value = results
    } else {
      agents.value = [...agents.value, ...results]
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
  if (loading.value || loadingMore.value || !hasMore.value) return
  await fetchAgents(false)
}

function selectCategory(cat: string) {
  selectedCategory.value = selectedCategory.value === cat ? '' : cat
  fetchAgents()
}

function selectSecurity(level: string) {
  selectedSecurity.value = selectedSecurity.value === level ? '' : level
  fetchAgents()
}

function setupObserver() {
  if (observer) observer.disconnect()

  observer = new IntersectionObserver(
    (entries) => {
      if (
        entries[0].isIntersecting &&
        hasMore.value &&
        !loading.value &&
        !loadingMore.value
      ) {
        loadMore()
      }
    },
    { threshold: 0.1 }
  )

  if (loadMoreTrigger.value) {
    observer.observe(loadMoreTrigger.value)
  }
}

watch(
  () => route.query,
  (q) => {
    selectedCategory.value = (q.category as string) || ''
    selectedSecurity.value = (q.security as string) || ''
    fetchAgents()
  },
  { immediate: true }
)

watch(loadMoreTrigger, () => {
  setupObserver()
})

onMounted(async () => {
  setupObserver()
  try {
    const res = await api.getCategories()
    categories.value = res.categories
  } catch (e) {
    console.error('Failed to load categories:', e)
  }
})

onUnmounted(() => {
  if (observer) observer.disconnect()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Agents</h1>
      <p class="text-gray-500 dark:text-gray-400">浏览和发现可用的 AI Agent 配置</p>
    </div>

    <div class="mb-4">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">分类</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="cat in categories"
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
        找到 {{ total.toLocaleString() }} 个结果
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 9" :key="i" class="card animate-pulse">
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-gray-100 dark:bg-gray-600 rounded w-1/2 mb-4"></div>
        <div class="h-16 bg-gray-100 dark:bg-gray-600 rounded"></div>
      </div>
    </div>

    <div v-else-if="agents.length === 0" class="text-center py-16">
      <p class="text-gray-500 dark:text-gray-400">没有找到匹配的 Agents</p>
      <p class="text-sm text-gray-400 dark:text-gray-500 mt-2">尝试其他分类或筛选条件</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <AgentCard v-for="agent in agents" :key="agent.id" :agent="agent" />
    </div>

    <div ref="loadMoreTrigger" class="h-10 flex items-center justify-center mt-6">
      <div v-if="loadingMore" class="animate-pulse text-gray-500 dark:text-gray-400">
        加载更多...
      </div>
      <div v-else-if="!hasMore" class="text-gray-400 dark:text-gray-500">
        没有更多了
      </div>
    </div>
  </div>
</template>
