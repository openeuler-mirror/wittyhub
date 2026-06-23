<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Agent } from '@/api/types'
import PlatformBadge from './PlatformBadge.vue'

defineProps<{
  agent: Agent
}>()

function truncate(text: string | null, length: number = 120): string {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}

function getAgentRoutePath(agentId: string): string {
  return `/agents/${encodeURIComponent(agentId)}`
}
</script>

<template>
  <RouterLink
    :to="getAgentRoutePath(agent.agent_id)"
    class="card block hover:border-primary-200 dark:hover:border-primary-400"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <h3 class="text-lg font-medium text-gray-900 truncate dark:text-white">{{ agent.name }}</h3>
          <span v-if="agent.verified" class="text-xs text-green-500">✓ Verified</span>
        </div>
        <p class="text-sm text-gray-500 mb-3 dark:text-gray-400">{{ agent.agent_id }}</p>
        <p class="text-gray-600 text-sm line-clamp-2 mb-3 dark:text-gray-300">
          {{ truncate(agent.description) }}
        </p>

        <div v-if="agent.supported_platforms?.length" class="flex flex-wrap gap-1 mb-3">
          <PlatformBadge
            v-for="platform in agent.supported_platforms.slice(0, 4)"
            :key="platform"
            :platform="platform"
            size="small"
          />
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <span
            v-if="agent.category"
            class="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded-full dark:bg-primary-900 dark:text-primary-300"
          >
            {{ agent.category }}
          </span>
          <span
            v-for="tag in (agent.tags || []).slice(0, 3)"
            :key="tag"
            class="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full dark:bg-gray-700 dark:text-gray-300"
          >
            {{ tag }}
          </span>
        </div>
      </div>
    </div>
    <div class="flex items-center gap-4 mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
      <span class="text-xs text-gray-400 dark:text-gray-500">
        <span class="inline-block mr-1">⬇</span>
        {{ agent.download_count.toLocaleString() }}
      </span>
      <span v-if="agent.star_count > 0" class="text-xs text-gray-400 dark:text-gray-500">
        <span class="inline-block mr-1">★</span>
        {{ agent.star_count.toLocaleString() }}
      </span>
      <span v-if="agent.license" class="text-xs text-gray-400 dark:text-gray-500">
        {{ agent.license }}
      </span>
      <a
        :href="agent.source_url"
        target="_blank"
        rel="noopener"
        class="text-xs text-gray-400 hover:text-primary-500 dark:text-gray-500 dark:hover:text-primary-400"
        @click.stop
      >
        {{ agent.source === 'github' ? 'GitHub' : agent.source === 'gitcode' ? 'GitCode' : agent.source }}
      </a>
    </div>
  </RouterLink>
</template>
