<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { Skill, SecurityAudit } from '@/api/types'
import SecurityBadge from '@/components/SecurityBadge.vue'

const route = useRoute()
const skill = ref<Skill | null>(null)
const versions = ref<Skill[]>([])
const audit = ref<SecurityAudit | null>(null)
const downloadUrl = ref('')
const loading = ref(true)
const error = ref('')
const selectedVersion = ref<string>('main')

onMounted(async () => {
  const repo = route.params.repo as string
  const name = route.params.name as string
  loading.value = true
  try {
    const versionsRes = await api.getSkillVersions(repo, name)
    versions.value = versionsRes.versions

    if (versionsRes.versions.length > 0) {
      selectedVersion.value = versionsRes.versions[0].version || 'main'
      const versionedSkillId = `${repo}/${name}:${selectedVersion.value}`
      skill.value = await api.getSkill(versionedSkillId)
      const auditRes = await api.getSkillAudit(versionedSkillId)
      if ('error' in auditRes) {
        audit.value = null
      } else {
        audit.value = auditRes
      }
      const dlRes = await api.getSkillDownload(versionedSkillId)
      downloadUrl.value = dlRes.download_url
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load skill'
  } finally {
    loading.value = false
  }
})

const selectVersion = async (version: string) => {
  const repo = route.params.repo as string
  const name = route.params.name as string
  selectedVersion.value = version
  const versionedSkillId = `${repo}/${name}:${version}`
  try {
    skill.value = await api.getSkill(versionedSkillId)
    const auditRes = await api.getSkillAudit(versionedSkillId)
    if ('error' in auditRes) {
      audit.value = null
    } else {
      audit.value = auditRes
    }
    const dlRes = await api.getSkillDownload(versionedSkillId)
    downloadUrl.value = dlRes.download_url
  } catch (e: any) {
    error.value = e.message || 'Failed to load skill'
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div v-if="loading" class="animate-pulse">
      <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
      <div class="h-4 bg-gray-100 dark:bg-gray-600 rounded w-1/4 mb-8"></div>
      <div class="h-32 bg-gray-100 dark:bg-gray-600 rounded mb-8"></div>
    </div>

    <div v-else-if="error" class="text-center py-16">
      <p class="text-red-500">{{ error }}</p>
    </div>

    <div v-else-if="skill" class="space-y-8">
      <!-- Header -->
      <div>
        <div class="flex items-center gap-3 mb-2">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ skill.name }}</h1>
          <SecurityBadge v-if="skill.security_score !== null" :score="skill.security_score" />
        </div>
        <p class="text-gray-500 dark:text-gray-400">{{ skill.skill_id }}</p>
      </div>

      <!-- Version Selector -->
      <div v-if="versions.length > 1" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
        <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">版本选择</h3>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="v in versions"
            :key="v.version || 'main'"
            @click="selectVersion(v.version || 'main')"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            :class="{
              'bg-blue-500 text-white': selectedVersion === v.version,
              'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600': selectedVersion !== v.version
            }"
          >
            {{ v.version }}{{ v.commit_id ? ` (${v.commit_id.slice(0, 7)})` : '' }}
          </button>
        </div>
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

      <!-- Content (skill.md) -->
      <div v-if="skill.content" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">详情</h2>
        <div class="prose dark:prose-invert max-w-none whitespace-pre-wrap text-gray-600 dark:text-gray-300">{{ skill.content }}</div>
      </div>

      <!-- Description -->
      <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">描述</h2>
        <p class="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ skill.description || '暂无描述' }}</p>
      </div>

      <!-- Meta -->
      <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">信息</h2>
        <dl class="grid grid-cols-2 gap-4">
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">分类</dt>
            <dd class="font-medium text-gray-900 dark:text-white">{{ skill.category || '-' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">平台</dt>
            <dd class="font-medium text-gray-900 dark:text-white">{{ skill.platform || '-' }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">来源</dt>
            <dd class="font-medium text-gray-900 dark:text-white">{{ skill.source }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">下载量</dt>
            <dd class="font-medium text-gray-900 dark:text-white">{{ skill.download_count.toLocaleString() }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">版本</dt>
            <dd class="font-medium text-gray-900 dark:text-white">{{ skill.version || '-' }}</dd>
          </div>
          <div v-if="skill.commit_id">
            <dt class="text-sm text-gray-500 dark:text-gray-400">Commit</dt>
            <dd class="font-medium text-gray-900 dark:text-white font-mono text-xs">{{ skill.commit_id }}</dd>
          </div>
        </dl>
      </div>

      <!-- Tags -->
      <div v-if="skill.tags?.length" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">标签</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="tag in skill.tags"
            :key="tag"
            class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm rounded-full"
          >
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- Security Report -->
      <div v-if="audit" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">安全报告</h2>
        <div class="space-y-4">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500 dark:text-gray-400">风险等级:</span>
            <span
              class="px-2 py-0.5 text-sm font-medium rounded"
              :class="{
                'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300': audit.risk_level === 'low',
                'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300': audit.risk_level === 'medium',
                'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300': audit.risk_level === 'high' || audit.risk_level === 'critical'
              }"
            >
              {{ audit.risk_level.toUpperCase() }}
            </span>
          </div>

          <div v-if="audit.risk_signals?.length" class="space-y-2">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">风险信号:</h3>
            <div
              v-for="signal in audit.risk_signals"
              :key="signal.id"
              class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm"
            >
              <span
                class="px-1.5 py-0.5 text-xs font-medium rounded mr-2"
                :class="{
                  'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300': signal.severity === 'High' || signal.severity === 'Critical',
                  'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300': signal.severity === 'Medium',
                  'bg-gray-100 text-gray-600 dark:bg-gray-600 dark:text-gray-300': signal.severity === 'Low'
                }"
              >
                {{ signal.severity }}
              </span>
              <span class="text-gray-700 dark:text-gray-200">{{ signal.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>