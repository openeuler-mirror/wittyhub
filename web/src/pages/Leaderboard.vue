<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import type { Skill, Agent } from '@/api/types'

const skills = ref<Skill[]>([])
const agents = ref<Agent[]>([])
const loading = ref(true)
const activeTab = ref<'agents' | 'skills'>('agents')

onMounted(async () => {
  try {
    const [skillsRes, agentsRes] = await Promise.all([
      api.listSkills({ limit: 100 }),
      api.listAgents({ limit: 100 })
    ])
    skills.value = skillsRes.skills
    agents.value = agentsRes.agents
  } catch (e) {
    console.error('Failed to load leaderboard:', e)
  } finally {
    loading.value = false
  }
})

const sortedAgents = computed(() =>
  [...agents.value].sort((a, b) => b.download_count - a.download_count)
)

const sortedSkills = computed(() =>
  [...skills.value].sort((a, b) => b.download_count - a.download_count)
)

function getAgentRoutePath(agentId: string): string {
  return `/agents/${encodeURIComponent(agentId)}`
}

function getSkillRoutePath(skillId: string): string {
  return `/skills/${encodeURIComponent(skillId)}`
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold text-gray-900 mb-8 dark:text-white">下载排行榜</h1>

    <!-- Tabs -->
    <div class="flex gap-4 mb-6">
      <button
        @click="activeTab = 'agents'"
        class="px-4 py-2 rounded-lg font-medium transition-colors"
        :class="activeTab === 'agents' ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'"
      >
        Agents
      </button>
      <button
        @click="activeTab = 'skills'"
        class="px-4 py-2 rounded-lg font-medium transition-colors"
        :class="activeTab === 'skills' ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'"
      >
        Skills
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 10" :key="i" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 p-4 animate-pulse">
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
      </div>
    </div>

    <!-- Agents Leaderboard -->
    <div v-else-if="activeTab === 'agents'" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div
        v-for="(agent, index) in sortedAgents"
        :key="agent.id"
        class="flex items-center gap-4 p-4 border-b border-gray-100 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
      >
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm"
          :class="{
            'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300': index === 0,
            'bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300': index === 1,
            'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300': index === 2,
            'bg-gray-50 text-gray-400 dark:bg-gray-700 dark:text-gray-400': index > 2
          }"
        >
          {{ index + 1 }}
        </div>
        <div class="flex-1 min-w-0">
          <RouterLink
            :to="getAgentRoutePath(agent.agent_id)"
            class="font-medium text-gray-900 hover:text-primary-500 dark:text-white dark:hover:text-primary-400"
          >
            {{ agent.name }}
          </RouterLink>
          <p class="text-sm text-gray-500 dark:text-gray-400">{{ agent.agent_id }}</p>
        </div>
        <div class="flex items-center gap-4 text-right">
          <div>
            <div class="font-medium text-gray-900 dark:text-white">
              {{ agent.download_count.toLocaleString() }}
            </div>
            <div class="text-xs text-gray-400 dark:text-gray-500">下载</div>
          </div>
          <div v-if="agent.star_count > 0">
            <div class="font-medium text-gray-900 dark:text-white">
              ★ {{ agent.star_count.toLocaleString() }}
            </div>
            <div class="text-xs text-gray-400 dark:text-gray-500">Stars</div>
          </div>
        </div>
      </div>
      <div v-if="sortedAgents.length === 0" class="p-8 text-center text-gray-500">
        暂无 Agent 数据
      </div>
    </div>

    <!-- Skills Leaderboard -->
    <div v-else class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div
        v-for="(skill, index) in sortedSkills"
        :key="skill.id"
        class="flex items-center gap-4 p-4 border-b border-gray-100 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
      >
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm"
          :class="{
            'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300': index === 0,
            'bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300': index === 1,
            'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300': index === 2,
            'bg-gray-50 text-gray-400 dark:bg-gray-700 dark:text-gray-400': index > 2
          }"
        >
          {{ index + 1 }}
        </div>
        <div class="flex-1 min-w-0">
          <RouterLink
            :to="getSkillRoutePath(skill.skill_id)"
            class="font-medium text-gray-900 hover:text-primary-500 dark:text-white dark:hover:text-primary-400"
          >
            {{ skill.name }}
          </RouterLink>
          <p class="text-sm text-gray-500 dark:text-gray-400">{{ skill.skill_id }}</p>
        </div>
        <div class="text-right">
          <div class="font-medium text-gray-900 dark:text-white">
            {{ skill.download_count.toLocaleString() }}
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-500">下载</div>
        </div>
      </div>
      <div v-if="sortedSkills.length === 0" class="p-8 text-center text-gray-500">
        暂无 Skill 数据
      </div>
    </div>
  </div>
</template>
