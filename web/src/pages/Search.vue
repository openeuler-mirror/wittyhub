<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SkillCard from '@/components/SkillCard.vue'
import { api } from '@/api/client'
import type { Skill } from '@/api/types'

const route = useRoute()
const router = useRouter()

const skills = ref<Skill[]>([])
const total = ref(0)
const loading = ref(false)
const query = ref('')
const selectedCategory = ref('')

const categories = ['DevTools', 'AI', 'Frontend', 'Backend', 'Cloud', 'Testing']

async function fetchSkills() {
  loading.value = true
  try {
    const res = await api.searchSkills({
      q: query.value || undefined,
      category: selectedCategory.value || undefined,
      limit: 20
    })
    skills.value = res.results
    total.value = res.total
  } catch (e) {
    console.error('Search failed:', e)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  router.push({ name: 'search', query: { q: query.value, category: selectedCategory.value } })
}

function selectCategory(cat: string) {
  selectedCategory.value = selectedCategory.value === cat ? '' : cat
  handleSearch()
}

watch(
  () => route.query,
  (q) => {
    query.value = (q.q as string) || ''
    selectedCategory.value = (q.category as string) || ''
    fetchSkills()
  },
  { immediate: true }
)
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <!-- Search Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 mb-4">搜索 Skills</h1>
      <form @submit.prevent="handleSearch" class="flex gap-4">
        <input
          v-model="query"
          type="text"
          placeholder="输入关键词搜索..."
          class="input flex-1"
        />
        <button type="submit" class="btn-primary">搜索</button>
      </form>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-2 mb-6">
      <button
        v-for="cat in categories"
        :key="cat"
        @click="selectCategory(cat)"
        class="px-3 py-1.5 text-sm rounded-full transition-colors"
        :class="selectedCategory === cat
          ? 'bg-primary-500 text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
      >
        {{ cat }}
      </button>
    </div>

    <!-- Results -->
    <div class="mb-4">
      <p class="text-sm text-gray-500">
        找到 {{ total.toLocaleString() }} 个结果
      </p>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 9" :key="i" class="card animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-gray-100 rounded w-1/2 mb-4"></div>
        <div class="h-16 bg-gray-100 rounded"></div>
      </div>
    </div>

    <div v-else-if="skills.length === 0" class="text-center py-16">
      <p class="text-gray-500">没有找到匹配的 Skills</p>
      <p class="text-sm text-gray-400 mt-2">尝试其他关键词或分类</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <SkillCard v-for="skill in skills" :key="skill.id" :skill="skill" />
    </div>
  </div>
</template>