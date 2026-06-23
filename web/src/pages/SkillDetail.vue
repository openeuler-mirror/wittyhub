<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { Skill, SecurityAudit } from '@/api/types'
import SecurityBadge from '@/components/SecurityBadge.vue'
import { marked } from 'marked'

function stripFrontmatter(content: string): string {
  const match = content.match(/^---\n[\s\S]*?\n---\n?/)
  if (match) {
    return content.slice(match[0].length).trim()
  }
  return content
}

const route = useRoute()
const skill = ref<Skill | null>(null)
const versions = ref<Skill[]>([])
const audit = ref<SecurityAudit | null>(null)
const loading = ref(true)
const error = ref('')
const selectedVersion = ref<string>('main')
const selectedCommitId = ref<string | null>(null)
const cliCopied = ref(false)

const currentSkillId = computed(() => {
  if (!skill.value?.skill_id) return ''
  return skill.value.skill_id
})

const renderedContent = computed(() => {
  if (!skill.value?.content) return ''
  return marked(stripFrontmatter(skill.value.content))
})

const downloadUrl = computed(() => {
  if (!skill.value) return ''
  const version = selectedVersion.value || 'main'
  const owner = skill.value.source_url.match(/github\.com\/([^\/]+)/)?.[1] || ''
  const repo = skill.value.source_url.match(/github\.com\/[^\/]+\/([^\/]+)/)?.[1] || ''
  const commitId = selectedCommitId.value
  if (commitId) {
    return `https://github.com/${owner}/${repo}/archive/${commitId}.zip`
  }
  return `https://github.com/${owner}/${repo}/archive/refs/heads/${version}.zip`
})

const browseUrl = computed(() => {
  if (!skill.value) return ''
  const version = selectedVersion.value || 'main'
  const owner = skill.value.source_url.match(/github\.com\/([^\/]+)/)?.[1] || ''
  const repo = skill.value.source_url.match(/github\.com\/[^\/]+\/([^\/]+)/)?.[1] || ''
  const skillName = skill.value.skill_id.split(':')[0].split('/').pop() || ''
  return `https://github.com/${owner}/${repo}/tree/${version}/skills/${skillName}`
})

onMounted(async () => {
  const path = route.params.path as string
  loading.value = true
  try {
    if (path) {
      const baseSkillId = path

      const firstColon = path.indexOf(':')
      const firstSlash = path.indexOf('/')

      let repo = ''
      let name = ''

      if (firstColon > 0 && (firstSlash === -1 || firstColon < firstSlash)) {
        const source = path.substring(0, firstColon)
        const remaining = path.substring(firstColon + 1)
        const slashIdx = remaining.indexOf('/')
        if (slashIdx > 0) {
          repo = source
          name = remaining
        } else {
          repo = source
          name = remaining
        }
      } else {
        repo = path
        name = path
      }

      const versionsRes = await api.getSkillVersions(repo, name)
      versions.value = versionsRes.versions

      if (versionsRes.versions.length > 0) {
        const latestVersion = versionsRes.versions[0]
        selectedVersion.value = latestVersion.version || 'main'
        selectedCommitId.value = latestVersion.commit_id
        skill.value = latestVersion
        const auditRes = await api.getSkillAudit(baseSkillId)
        if ('error' in auditRes) {
          audit.value = null
        } else {
          audit.value = auditRes
        }
      } else {
        skill.value = await api.getSkill(baseSkillId)
        if (skill.value) {
          const auditRes = await api.getSkillAudit(baseSkillId)
          if ('error' in auditRes) {
            audit.value = null
          } else {
            audit.value = auditRes
          }
        }
      }
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load skill'
  } finally {
    loading.value = false
  }
})

const selectVersion = async (version: string) => {
  selectedVersion.value = version
  const versionObj = versions.value.find(v => v.version === version)
  selectedCommitId.value = versionObj?.commit_id || null
  if (versionObj) {
    skill.value = versionObj
    const baseSkillId = skill.value.skill_id.split(':').slice(0, 2).join(':')
    const auditRes = await api.getSkillAudit(baseSkillId)
    if ('error' in auditRes) {
      audit.value = null
    } else {
      audit.value = auditRes
    }
  }
}


const copyCliCommand = async () => {
  const command = `skillhub install ${currentSkillId.value}`
  try {
    await navigator.clipboard.writeText(command)
    cliCopied.value = true
    setTimeout(() => { cliCopied.value = false }, 2000)
  } catch (e) {
    console.error('Failed to copy:', e)
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div v-if="loading" class="animate-pulse">
      <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
      <div class="h-4 bg-gray-100 dark:bg-gray-600 rounded w-1/4 mb-8"></div>
      <div class="h-32 bg-gray-100 dark:bg-gray-600 rounded mb-8"></div>
    </div>

    <div v-else-if="error" class="text-center py-16">
      <p class="text-red-500">{{ error }}</p>
    </div>

    <div v-else-if="skill" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left Column - Main Info (2/3) -->
      <div class="lg:col-span-2 space-y-6">
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
        <div class="space-y-4">
          <div class="flex flex-wrap gap-3">
            <a
              :href="downloadUrl"
              target="_blank"
              class="btn-primary"
            >
              📦 下载 ZIP {{ selectedCommitId ? `(commit: ${selectedCommitId.slice(0, 7)})` : '' }}
            </a>
            <a
              :href="browseUrl"
              target="_blank"
              rel="noopener"
              class="btn-secondary"
            >
              🌐 浏览仓库
            </a>
          </div>

          <!-- CLI Install -->
          <div v-if="currentSkillId" class="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">CLI 安装</h3>
            <div class="flex items-center gap-2">
              <code class="flex-1 bg-gray-200 dark:bg-gray-700 rounded px-3 py-2 text-sm font-mono text-gray-800 dark:text-gray-200 overflow-x-auto">
                skillhub install {{ currentSkillId }}
              </code>
              <button
                @click="copyCliCommand"
                class="px-3 py-2 bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 rounded text-sm"
              >
                {{ cliCopied ? '✓ 已复制' : '复制' }}
              </button>
            </div>
            <p class="text-xs text-gray-500 mt-2">安装到 ~/.agents/skills/ 目录</p>
          </div>
        </div>

        <!-- Description -->
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">描述</h2>
          <p class="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ skill.description || '暂无描述' }}</p>
        </div>

        <!-- Content (skill.md) -->
        <div v-if="skill.content" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">详情</h2>
          <div class="prose dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 text-sm" v-html="renderedContent"></div>
        </div>
        <div v-else class="bg-gray-100 dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6 text-center">
          <p class="text-gray-500 dark:text-gray-400">暂无详情内容</p>
          <p class="text-xs text-gray-400 mt-2">内容将在本地安装后显示</p>
        </div>
      </div>

      <!-- Right Column - Sidebar (1/3) -->
      <div class="lg:col-span-1 space-y-6">
        <!-- Meta -->
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">信息</h2>
          <dl class="space-y-3">
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
  </div>
</template>