<script setup lang="ts">
import type { SubagentConfig } from '@/api/types'

defineProps<{
  subagents: SubagentConfig[]
}>()
</script>

<template>
  <div class="space-y-4">
    <div
      v-for="subagent in subagents"
      :key="subagent.name"
      class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4"
    >
      <h4 class="font-medium text-gray-900 dark:text-white mb-2">{{ subagent.name }}</h4>

      <div v-if="subagent.prompt?.system" class="mb-3">
        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">System Prompt</p>
        <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ subagent.prompt.system }}</p>
      </div>

      <div v-if="subagent.prompt?.identity" class="mb-3">
        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Identity</p>
        <div class="flex flex-wrap gap-2 text-sm text-gray-600 dark:text-gray-300">
          <span v-if="subagent.prompt.identity.role">Role: {{ subagent.prompt.identity.role }}</span>
          <span v-if="subagent.prompt.identity.emoji">Emoji: {{ subagent.prompt.identity.emoji }}</span>
          <span v-if="subagent.prompt.identity.vibe">Vibe: {{ subagent.prompt.identity.vibe }}</span>
        </div>
      </div>

      <div v-if="subagent.skills?.length" class="mb-3">
        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Skills</p>
        <div class="flex flex-wrap gap-1">
          <span
            v-for="skill in subagent.skills"
            :key="skill.name"
            class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded-full"
          >
            {{ skill.name }}
            <span v-if="skill.when?.length" class="text-gray-400 dark:text-gray-500">
              (when: {{ skill.when.join(', ') }})
            </span>
          </span>
        </div>
      </div>

      <div v-if="subagent.tools?.allowed?.length">
        <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Tools</p>
        <div class="flex flex-wrap gap-1">
          <span
            v-for="tool in subagent.tools.allowed"
            :key="tool"
            class="px-2 py-0.5 bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-300 text-xs rounded-full"
          >
            {{ tool }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
