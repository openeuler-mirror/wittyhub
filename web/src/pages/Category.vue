<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SkillCard from '@/components/SkillCard.vue'
import { api } from '@/api/client'
import type { Skill } from '@/api/types'

const route = useRoute()
const skills = ref<Skill[]>([])
const total = ref(0)
const loading = ref(false)

async function fetchByCategory(cat: string) {
  loading.value = true
  try {
    const res = await api.searchSkills({ category: cat, limit: 50 })
    skills.value = res.results
    total.value = res.total
  } catch (e) {
    console.error('Failed to load category:', e)
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.category,
  (cat) => {
    if (cat) fetchByCategory(cat as string)
  },
  { immediate: true }
)
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 mb-2">
        {{ route.params.category }}
      </h1>
      <p class="text-gray-500">{{ total.toLocaleString() }} 个 Skills</p>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 9" :key="i" class="card animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-gray-100 rounded w-1/2 mb-4"></div>
        <div class="h-16 bg-gray-100 rounded"></div>
      </div>
    </div>

    <div v-else-if="skills.length === 0" class="text-center py-16">
      <p class="text-gray-500">该分类下暂无 Skills</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <SkillCard v-for="skill in skills" :key="skill.id" :skill="skill" />
    </div>
  </div>
</template>