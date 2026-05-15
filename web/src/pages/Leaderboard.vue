<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import type { Skill } from '@/api/types'

const skills = ref<Skill[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.listSkills({ limit: 20 })
    skills.value = res.skills.sort((a, b) => b.download_count - a.download_count)
  } catch (e) {
    console.error('Failed to load leaderboard:', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">下载排行榜</h1>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 10" :key="i" class="bg-white rounded-lg border p-4 animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-1/4"></div>
      </div>
    </div>

    <div v-else class="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <div
        v-for="(skill, index) in skills"
        :key="skill.id"
        class="flex items-center gap-4 p-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50"
      >
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm"
          :class="{
            'bg-yellow-100 text-yellow-700': index === 0,
            'bg-gray-200 text-gray-600': index === 1,
            'bg-orange-100 text-orange-700': index === 2,
            'bg-gray-50 text-gray-400': index > 2
          }"
        >
          {{ index + 1 }}
        </div>
        <div class="flex-1 min-w-0">
          <RouterLink
            :to="`/skills/${encodeURIComponent(skill.skill_id)}`"
            class="font-medium text-gray-900 hover:text-primary-500"
          >
            {{ skill.name }}
          </RouterLink>
          <p class="text-sm text-gray-500">{{ skill.skill_id }}</p>
        </div>
        <div class="text-right">
          <div class="font-medium text-gray-900">
            {{ skill.download_count.toLocaleString() }}
          </div>
          <div class="text-xs text-gray-400">下载</div>
        </div>
      </div>
    </div>
  </div>
</template>