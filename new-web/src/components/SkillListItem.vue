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
    class="flex items-center gap-4 px-4 py-3 border-b border-gray-200 bg-white hover:bg-gray-50 transition-colors last:border-b-0 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 group"
  >
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 mb-1">
        <h3 class="text-sm font-medium text-gray-900 group-hover:text-primary-500 transition-colors truncate dark:text-white">
          {{ skill.name }}
        </h3>
        <span :class="['tag', securityLevel.class]">{{ securityLevel.label }}</span>
      </div>
      <p class="text-xs text-gray-500 truncate dark:text-gray-400">
        {{ truncate(skill.description, 100) }}
      </p>
    </div>

    <div class="hidden md:block w-24 text-left">
      <span v-if="skill.category" class="tag tag-blue">{{ skill.category }}</span>
    </div>

    <div class="hidden sm:block w-20 text-left">
      <span :class="['tag', securityLevel.class]">{{ securityLevel.label }}</span>
    </div>

    <div class="hidden sm:flex w-20 text-sm text-gray-500 dark:text-gray-400 items-center justify-start gap-1">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="flex-shrink-0">
        <path d="M12 3.29492C12.3544 3.29492 12.6473 3.55827 12.6936 3.89994L12.7 3.99492L12.7 15.5335L17.2249 10.9581C17.4968 10.6833 17.94 10.6808 18.2149 10.9526C18.4623 11.1973 18.489 11.5808 18.2937 11.8554L18.2204 11.9426L12.5008 17.726C12.3635 17.8647 12.1825 17.9341 12.0016 17.9337L12 17.9337C11.6456 17.9337 11.3527 17.6704 11.3064 17.3287L11.3 17.2337L11.3 3.99492C11.3 3.60832 11.6134 3.29492 12 3.29492ZM6.68698 10.8826C6.41393 10.6851 6.03026 10.7087 5.78362 10.9541C5.50957 11.2268 5.50845 11.67 5.78113 11.9441L8.73786 14.9157L8.82444 14.9897C9.09749 15.1872 9.48116 15.1636 9.72781 14.9182C10.0019 14.6455 10.003 14.2023 9.73029 13.9282L6.77356 10.9566L6.68698 10.8826ZM19.0079 19.3594C19.3945 19.3594 19.7079 19.6728 19.7079 20.0594C19.7079 20.4138 19.4445 20.7066 19.1028 20.753L19.0079 20.7594L5.01445 20.7594C4.62785 20.7594 4.31445 20.446 4.31445 20.0594C4.31445 19.705 4.5778 19.4121 4.91947 19.3658L5.01445 19.3594L19.0079 19.3594Z" fill="currentColor" fill-rule="evenodd"/>
      </svg>
      {{ skill.download_count.toLocaleString() }}
    </div>

    <div class="hidden lg:block w-24 text-left text-sm text-gray-500 truncate dark:text-gray-400">
      {{ skill.source }}
    </div>
  </RouterLink>
</template>

<style scoped>
/* Risk level tag styles matching OTag design */
.tag-blue {
  @apply bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400;
}
.tag-green {
  @apply bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400;
}
.tag-orange {
  @apply bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400;
}
.tag-red {
  @apply bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400;
}
.tag-gray {
  @apply bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300;
}
</style>
