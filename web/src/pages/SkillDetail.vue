<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { Skill, SecurityAudit } from '@/api/types'
import SecurityBadge from '@/components/SecurityBadge.vue'

const route = useRoute()
const skill = ref<Skill | null>(null)
const audit = ref<SecurityAudit | null>(null)
const downloadUrl = ref('')
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  const slug = decodeURIComponent(route.params.slug as string)
  loading.value = true
  try {
    skill.value = await api.getSkill(slug)
    const auditRes = await api.getSkillAudit(slug)
    if ('error' in auditRes) {
      audit.value = null
    } else {
      audit.value = auditRes
    }
    const dlRes = await api.getSkillDownload(slug)
    downloadUrl.value = dlRes.download_url
  } catch (e: any) {
    error.value = e.message || 'Failed to load skill'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div v-if="loading" class="animate-pulse">
      <div class="h-8 bg-gray-200 rounded w-1/2 mb-4"></div>
      <div class="h-4 bg-gray-100 rounded w-1/4 mb-8"></div>
      <div class="h-32 bg-gray-100 rounded mb-8"></div>
    </div>

    <div v-else-if="error" class="text-center py-16">
      <p class="text-red-500">{{ error }}</p>
    </div>

    <div v-else-if="skill" class="space-y-8">
      <!-- Header -->
      <div>
        <div class="flex items-center gap-3 mb-2">
          <h1 class="text-3xl font-bold text-gray-900">{{ skill.name }}</h1>
          <SecurityBadge v-if="skill.security_score !== null" :score="skill.security_score" />
        </div>
        <p class="text-gray-500">{{ skill.skill_id }}</p>
      </div>

      <!-- Actions -->
      <div class="flex flex-wrap gap-3">
        <a
          :href="downloadUrl"
          target="_blank"
          class="btn-primary"
        >
          📥 访问仓库
        </a>
        <a
          :href="skill.source_url"
          target="_blank"
          rel="noopener"
          class="btn-secondary"
        >
          🔗 查看源地址
        </a>
      </div>

      <!-- Description -->
      <div class="bg-white rounded-xl border border-gray-100 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-3">描述</h2>
        <p class="text-gray-600 whitespace-pre-wrap">{{ skill.description || '暂无描述' }}</p>
      </div>

      <!-- Meta -->
      <div class="bg-white rounded-xl border border-gray-100 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-3">信息</h2>
        <dl class="grid grid-cols-2 gap-4">
          <div>
            <dt class="text-sm text-gray-500">分类</dt>
            <dd class="font-medium">{{ skill.category || '-' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">平台</dt>
            <dd class="font-medium">{{ skill.platform || '-' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">来源</dt>
            <dd class="font-medium">{{ skill.source }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">下载量</dt>
            <dd class="font-medium">{{ skill.download_count.toLocaleString() }}</dd>
          </div>
        </dl>
      </div>

      <!-- Tags -->
      <div v-if="skill.tags?.length" class="bg-white rounded-xl border border-gray-100 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-3">标签</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="tag in skill.tags"
            :key="tag"
            class="px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded-full"
          >
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- Security Report -->
      <div v-if="audit" class="bg-white rounded-xl border border-gray-100 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-3">安全报告</h2>
        <div class="space-y-4">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500">风险等级:</span>
            <span
              class="px-2 py-0.5 text-sm font-medium rounded"
              :class="{
                'bg-green-100 text-green-700': audit.risk_level === 'low',
                'bg-yellow-100 text-yellow-700': audit.risk_level === 'medium',
                'bg-red-100 text-red-700': audit.risk_level === 'high' || audit.risk_level === 'critical'
              }"
            >
              {{ audit.risk_level.toUpperCase() }}
            </span>
          </div>

          <div v-if="audit.risk_signals?.length" class="space-y-2">
            <h3 class="text-sm font-medium text-gray-700">风险信号:</h3>
            <div
              v-for="signal in audit.risk_signals"
              :key="signal.id"
              class="p-3 bg-gray-50 rounded-lg text-sm"
            >
              <span
                class="px-1.5 py-0.5 text-xs font-medium rounded mr-2"
                :class="{
                  'bg-red-100 text-red-700': signal.severity === 'High' || signal.severity === 'Critical',
                  'bg-yellow-100 text-yellow-700': signal.severity === 'Medium',
                  'bg-gray-100 text-gray-600': signal.severity === 'Low'
                }"
              >
                {{ signal.severity }}
              </span>
              {{ signal.name }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>