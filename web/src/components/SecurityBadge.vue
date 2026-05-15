<script setup lang="ts">
const props = defineProps<{
  score: number | null
}>()

function getLevel(score: number | null): { label: string; color: string } {
  if (score === null) return { label: 'Unknown', color: 'gray' }
  if (score >= 80) return { label: 'Safe', color: 'green' }
  if (score >= 60) return { label: 'Low', color: 'yellow' }
  if (score >= 40) return { label: 'Medium', color: 'orange' }
  return { label: 'High Risk', color: 'red' }
}

const level = getLevel(props.score)
</script>

<template>
  <span
    class="px-2 py-0.5 text-xs font-medium rounded"
    :class="{
      'bg-green-100 text-green-700': level.color === 'green',
      'bg-yellow-100 text-yellow-700': level.color === 'yellow',
      'bg-orange-100 text-orange-700': level.color === 'orange',
      'bg-red-100 text-red-700': level.color === 'red',
      'bg-gray-100 text-gray-600': level.color === 'gray'
    }"
  >
    {{ level.label }}
  </span>
</template>