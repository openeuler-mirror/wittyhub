<script setup lang="ts">
defineProps<{
  platform: string
  size?: 'small' | 'normal'
}>()

const platformLabels: Record<string, { label: string; color: string }> = {
  'claude-code': { label: 'Claude Code', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' },
  'opencode': { label: 'OpenCode', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  'openclaw': { label: 'OpenClaw', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
  'sdk': { label: 'SDK', color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' }
}

function getPlatformInfo(platform: string) {
  return platformLabels[platform] || { label: platform, color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' }
}
</script>

<template>
  <span
    :class="[
      size === 'small' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-0.5 text-xs',
      getPlatformInfo(platform).color,
      'rounded-full'
    ]"
  >
    {{ getPlatformInfo(platform).label }}
  </span>
</template>
