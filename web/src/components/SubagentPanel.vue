<script setup lang="ts">
import type { SubagentConfig } from '@/api/types'

defineProps<{
  subagent: SubagentConfig
}>()

function truncate(text: string | null, length: number = 200): string {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}
</script>

<template>
  <details class="subagent-panel border border-gray-200 dark:border-gray-700 rounded-lg">
    <summary class="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 list-none">
      <span class="text-xl">{{ subagent.prompt?.identity?.emoji || '🤖' }}</span>
      <div class="flex-1">
        <div class="flex items-center gap-2">
          <span class="font-medium text-gray-900 dark:text-white">{{ subagent.name }}</span>
          <span
            v-if="subagent.prompt?.identity?.role"
            class="text-sm text-gray-500 dark:text-gray-400"
          >
            {{ subagent.prompt.identity.role }}
          </span>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="subagent.skills?.length"
          class="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full dark:bg-blue-900 dark:text-blue-300"
        >
          {{ subagent.skills.length }} skills
        </span>
        <span
          v-if="subagent.tools?.allowed?.length"
          class="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full dark:bg-green-900 dark:text-green-300"
        >
          {{ subagent.tools.allowed.length }} tools
        </span>
        <span class="text-gray-400">▼</span>
      </div>
    </summary>

    <div class="p-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
      <div v-if="subagent.skills?.length">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Skills</h4>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="skill in subagent.skills"
            :key="skill.name"
            class="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded dark:bg-gray-700 dark:text-gray-300"
          >
            {{ skill.name }}
          </span>
        </div>
      </div>

      <div v-if="subagent.tools?.allowed?.length">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tools</h4>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="tool in subagent.tools.allowed"
            :key="tool"
            class="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded dark:bg-gray-700 dark:text-gray-300 font-mono"
          >
            {{ tool }}
          </span>
        </div>
      </div>

      <details v-if="subagent.prompt?.system" class="border border-gray-200 dark:border-gray-600 rounded">
        <summary class="px-3 py-2 cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 list-none">
          System Prompt
        </summary>
        <div class="p-3 border-t border-gray-200 dark:border-gray-600">
          <pre class="whitespace-pre-wrap text-sm text-gray-600 dark:text-gray-300 font-mono">{{ truncate(subagent.prompt.system, 500) }}</pre>
        </div>
      </details>
    </div>
  </details>
</template>
