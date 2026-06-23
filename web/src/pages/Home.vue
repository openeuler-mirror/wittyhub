<script setup lang="ts">
import { ref, onMounted } from 'vue'
import CategoryNav from '@/components/CategoryNav.vue'
import SkillCard from '@/components/SkillCard.vue'
import AgentCard from '@/components/AgentCard.vue'
import { api } from '@/api/client'
import type { Skill, Agent } from '@/api/types'

const trendingSkills = ref<Skill[]>([])
const trendingAgents = ref<Agent[]>([])
const loading = ref(true)
const stats = ref({ total_skills: 0, total_categories: 0 })

onMounted(async () => {
  try {
    const [skillsRes, statsRes, agentsRes] = await Promise.all([
      api.listSkills({ limit: 6 }),
      api.getStats(),
      api.listAgents({ limit: 6 })
    ])
    trendingSkills.value = skillsRes.skills
    trendingAgents.value = agentsRes.agents
    stats.value = statsRes
  } catch (e) {
    console.error('Failed to load data:', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <!-- Hero Section -->
    <section class="bg-gradient-to-br from-primary-500 to-primary-700 text-white">
      <div class="max-w-7xl mx-auto px-4 py-16">
        <div class="text-center mb-8">
          <h1 class="text-4xl md:text-5xl font-bold mb-4">
            发现 AI Agents & Skills
          </h1>
          <p class="text-xl text-primary-100 max-w-2xl mx-auto">
            探索、评估和获取可复用的 AI Agents 和 Skills。支持分类浏览、安全检测。
          </p>
        </div>
      </div>
    </section>

    <!-- Categories -->
    <section class="max-w-7xl mx-auto px-4 py-12 dark:bg-gray-900">
      <h2 class="text-2xl font-bold text-gray-900 mb-6 dark:text-white">分类浏览</h2>
      <CategoryNav />
    </section>

    <!-- Trending Agents -->
    <section class="max-w-7xl mx-auto px-4 py-12">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">热门 Agents</h2>
        <RouterLink
          to="/agents/"
          class="text-primary-500 hover:text-primary-600 font-medium"
        >
          查看更多 →
        </RouterLink>
      </div>

      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 3" :key="i" class="card animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2 dark:bg-gray-700"></div>
          <div class="h-3 bg-gray-100 rounded w-1/2 mb-4 dark:bg-gray-600"></div>
          <div class="h-16 bg-gray-100 rounded dark:bg-gray-600"></div>
        </div>
      </div>

      <div v-else-if="trendingAgents.length === 0" class="text-center py-8">
        <p class="text-gray-500 dark:text-gray-400">暂无 Agent 数据</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <AgentCard v-for="agent in trendingAgents" :key="agent.id" :agent="agent" />
      </div>
    </section>

    <!-- Trending Skills -->
    <section class="max-w-7xl mx-auto px-4 py-12 bg-gray-50 dark:bg-gray-800">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">热门 Skills</h2>
        <RouterLink
          to="/skills/search"
          class="text-primary-500 hover:text-primary-600 font-medium"
        >
          查看更多 →
        </RouterLink>
      </div>

      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="card animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2 dark:bg-gray-700"></div>
          <div class="h-3 bg-gray-100 rounded w-1/2 mb-4 dark:bg-gray-600"></div>
          <div class="h-16 bg-gray-100 rounded dark:bg-gray-600"></div>
        </div>
      </div>

      <div v-else-if="trendingSkills.length === 0" class="text-center py-8">
        <p class="text-gray-500 dark:text-gray-400">暂无 Skill 数据</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <SkillCard v-for="skill in trendingSkills" :key="skill.id" :skill="skill" />
      </div>
    </section>

    <!-- Stats -->
    <section class="bg-white border-y border-gray-200 dark:bg-gray-900 dark:border-gray-700">
      <div class="max-w-7xl mx-auto px-4 py-12">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div class="text-3xl font-bold text-primary-500">{{ stats.total_skills.toLocaleString() }}+</div>
            <div class="text-gray-500 text-sm mt-1 dark:text-gray-400">已收录 Skills</div>
          </div>
          <div>
            <div class="text-3xl font-bold text-primary-500">{{ stats.total_categories }}+</div>
            <div class="text-gray-500 text-sm mt-1 dark:text-gray-400">涵盖分类</div>
          </div>
          <div>
            <div class="text-3xl font-bold text-primary-500">50+</div>
            <div class="text-gray-500 text-sm mt-1 dark:text-gray-400">AI Agents</div>
          </div>
          <div>
            <div class="text-3xl font-bold text-primary-500">安全</div>
            <div class="text-gray-500 text-sm mt-1 dark:text-gray-400">安全检测</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
