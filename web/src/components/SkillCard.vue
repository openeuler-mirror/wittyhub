<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Skill } from '@/api/types'
import SecurityBadge from './SecurityBadge.vue'

defineProps<{
  skill: Skill
}>()

function truncate(text: string | null, length: number = 120): string {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}
</script>

<template>
  <RouterLink
    :to="`/skills/${encodeURIComponent(skill.skill_id)}`"
    class="card block hover:border-primary-200 dark:hover:border-primary-400"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <h3 class="text-lg font-medium text-gray-900 truncate dark:text-white">{{ skill.name }}</h3>
          <SecurityBadge v-if="skill.security_score !== null" :score="skill.security_score" />
        </div>
        <p class="text-sm text-gray-500 mb-3 dark:text-gray-400">{{ skill.skill_id }}</p>
        <p class="text-gray-600 text-sm line-clamp-2 mb-3 dark:text-gray-300">
          {{ truncate(skill.description) }}
        </p>
        <div class="flex flex-wrap items-center gap-2">
          <span
            v-if="skill.category"
            class="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded-full dark:bg-primary-900 dark:text-primary-300"
          >
            {{ skill.category }}
          </span>
          <span
            v-for="tag in (skill.tags || []).slice(0, 3)"
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
        {{ skill.download_count.toLocaleString() }}
      </span>
      <a
        :href="skill.source_url"
        target="_blank"
        rel="noopener"
        class="text-xs text-gray-400 hover:text-primary-500 dark:text-gray-500 dark:hover:text-primary-400"
        @click.stop
      >
        {{ skill.source === 'github' ? 'GitHub' : skill.source }}
      </a>
    </div>
  </RouterLink>
</template>