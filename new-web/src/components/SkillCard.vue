<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Skill } from '@/api/types'

const props = defineProps<{
  skill: Skill
}>()

function getSkillRoutePath(skillId: string): string {
  return `/skills/${encodeURIComponent(skillId)}`
}

function getSecurityLevel(score: number | null): { label: string; class: string } {
  if (score === null) return { label: '未检测', class: 'tag-gray' }
  if (score <= 20) return { label: '安全', class: 'tag-green' }
  if (score <= 50) return { label: '低风险', class: 'tag-blue' }
  if (score <= 80) return { label: '中风险', class: 'tag-orange' }
  return { label: '高风险', class: 'tag-red' }
}

const securityLevel = computed(() => getSecurityLevel(props.skill.risk_score))

function truncate(text: string | null, length: number): string {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}
</script>

<template>
  <RouterLink
    :to="getSkillRoutePath(skill.skill_id)"
    class="card card-hover block p-4 group"
  >
    <div class="flex items-start justify-between mb-3">
      <div class="flex items-center gap-2">
        <h3 class="text-base font-medium text-gray-900 group-hover:text-primary-500 transition-colors dark:text-white">
          {{ skill.name }}
        </h3>
        <span :class="['tag', securityLevel.class]">{{ securityLevel.label }}</span>
      </div>
    </div>

    <p class="text-xs text-gray-500 mb-3 dark:text-gray-400">{{ skill.skill_id }}</p>

    <p class="text-sm text-gray-600 line-clamp-2 mb-4 dark:text-gray-300">
      {{ truncate(skill.description, 120) }}
    </p>

    <div class="flex flex-wrap gap-1.5 mb-4">
      <span
        v-if="skill.category"
        class="tag tag-blue"
      >
        {{ skill.category }}
      </span>
      <span
        v-for="tag in (skill.tags || []).slice(0, 3)"
        :key="tag"
        class="tag tag-gray"
      >
        {{ tag }}
      </span>
    </div>

    <div class="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
      <div class="flex items-center gap-1 text-xs text-gray-400">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 3.29492C12.3544 3.29492 12.6473 3.55827 12.6936 3.89994L12.7 3.99492L12.7 15.5335L17.2249 10.9581C17.4968 10.6833 17.94 10.6808 18.2149 10.9526C18.4623 11.1973 18.489 11.5808 18.2937 11.8554L18.2204 11.9426L12.5008 17.726C12.3635 17.8647 12.1825 17.9341 12.0016 17.9337L12 17.9337C11.6456 17.9337 11.3527 17.6704 11.3064 17.3287L11.3 17.2337L11.3 3.99492C11.3 3.60832 11.6134 3.29492 12 3.29492ZM6.68698 10.8826C6.41393 10.6851 6.03026 10.7087 5.78362 10.9541C5.50957 11.2268 5.50845 11.67 5.78113 11.9441L8.73786 14.9157L8.82444 14.9897C9.09749 15.1872 9.48116 15.1636 9.72781 14.9182C10.0019 14.6455 10.003 14.2023 9.73029 13.9282L6.77356 10.9566L6.68698 10.8826ZM19.0079 19.3594C19.3945 19.3594 19.7079 19.6728 19.7079 20.0594C19.7079 20.4138 19.4445 20.7066 19.1028 20.753L19.0079 20.7594L5.01445 20.7594C4.62785 20.7594 4.31445 20.446 4.31445 20.0594C4.31445 19.705 4.5778 19.4121 4.91947 19.3658L5.01445 19.3594L19.0079 19.3594Z" fill="currentColor" fill-rule="evenodd"/>
        </svg>
        <span>{{ skill.download_count.toLocaleString() }}</span>
      </div>
      <div class="flex items-center gap-1 text-xs text-gray-400">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
        </svg>
        <span>{{ skill.source }}</span>
      </div>
    </div>
  </RouterLink>
</template>
