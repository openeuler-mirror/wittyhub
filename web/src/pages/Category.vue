<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import SkillCard from '@/components/SkillCard.vue'
import { api } from '@/api/client'
import type { Skill } from '@/api/types'

const route = useRoute()
const skills = ref<Skill[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const skip = ref(0)
const limit = 50
const hasMore = ref(true)
let observer: IntersectionObserver | null = null
const loadMoreTrigger = ref<HTMLElement | null>(null)

async function fetchByCategory(cat: string, reset = true) {
  if (reset) {
    loading.value = true
    skip.value = 0
    hasMore.value = true
  } else {
    loadingMore.value = true
  }

  try {
    const res = await api.listSkills({
      skip: skip.value,
      limit: limit,
      category: cat,
    })
    if (reset) {
      skills.value = res.skills
    } else {
      skills.value = [...skills.value, ...res.skills]
    }
    total.value = res.total
    hasMore.value = skills.value.length < res.total
    skip.value += res.skills.length
  } catch (e) {
    console.error('Failed to load category:', e)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  const cat = route.params.category as string
  if (cat) await fetchByCategory(cat, false)
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

watch(
  () => route.params.category,
  (cat) => {
    if (cat) fetchByCategory(cat as string)
  },
  { immediate: true }
)

watch(loadMoreTrigger, () => {
  setupObserver()
})

onMounted(() => {
  setupObserver()
})

onUnmounted(() => {
  if (observer) observer.disconnect()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 mb-2 dark:text-white">
        {{ route.params.category }}
      </h1>
      <p class="text-gray-500 dark:text-gray-400">{{ total.toLocaleString() }} 个 Skills</p>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 9" :key="i" class="card animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-3/4 mb-2 dark:bg-gray-700"></div>
        <div class="h-3 bg-gray-100 rounded w-1/2 mb-4 dark:bg-gray-600"></div>
        <div class="h-16 bg-gray-100 rounded dark:bg-gray-600"></div>
      </div>
    </div>

    <div v-else-if="skills.length === 0" class="text-center py-16">
      <p class="text-gray-500 dark:text-gray-400">该分类下暂无 Skills</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <SkillCard v-for="skill in skills" :key="skill.id" :skill="skill" />
    </div>

    <div ref="loadMoreTrigger" class="h-10 flex items-center justify-center mt-6">
      <div v-if="loadingMore" class="animate-pulse text-gray-500 dark:text-gray-400">
        加载更多...
      </div>
      <div v-else-if="!hasMore && skills.length > 0" class="text-gray-400 dark:text-gray-500">
        没有更多了
      </div>
    </div>
  </div>
</template>