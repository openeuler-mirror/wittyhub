<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { Agent, AgentVersion } from '@/api/types'
import PlatformBadge from '@/components/PlatformBadge.vue'
import SubagentPanel from '@/components/SubagentPanel.vue'
import { marked } from 'marked'

function stripFrontmatter(content: string): string {
  const match = content.match(/^---\n[\s\S]*?\n---\n?/)
  if (match) {
    return content.slice(match[0].length).trim()
  }
  return content
}

const route = useRoute()
const agent = ref<Agent | null>(null)
const versions = ref<AgentVersion[]>([])
const loading = ref(true)
const error = ref('')

const routeAgentId = computed(() => {
  const raw = route.params.path
  if (Array.isArray(raw)) return raw.join('/')
  return (raw as string) || ''
})

const renderedContent = computed(() => {
  if (!agent.value?.readme_content) return ''
  return marked(stripFrontmatter(agent.value.readme_content))
})

const installCommand = computed(() => {
  if (!agent.value) return ''
  return `npx wittyhub agent install ${agent.value.agent_id}`
})

onMounted(async () => {
  const agentId = routeAgentId.value
  loading.value = true
  try {
    if (!agentId) {
      throw new Error('Missing agent id')
    }

    const [agentRes, versionsRes] = await Promise.all([
      api.getAgent(agentId),
      api.getAgentVersions(agentId)
    ])
    agent.value = agentRes
    versions.value = versionsRes.versions
  } catch (e: any) {
    error.value = e.message || 'Failed to load agent'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div v-if="loading" class="animate-pulse">
      <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
      <div class="h-4 bg-gray-100 dark:bg-gray-600 rounded w-1/4 mb-8"></div>
      <div class="h-32 bg-gray-100 dark:bg-gray-600 rounded mb-8"></div>
      <div class="grid grid-cols-3 gap-8">
        <div class="col-span-2 h-64 bg-gray-100 dark:bg-gray-600 rounded"></div>
        <div class="col-span-1 h-64 bg-gray-100 dark:bg-gray-600 rounded"></div>
      </div>
    </div>

    <div v-else-if="error" class="text-center py-16">
      <p class="text-red-500">{{ error }}</p>
    </div>

    <div v-else-if="agent" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left Column - Main Info (2/3) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Header -->
        <div class="flex items-start gap-4">
          <div v-if="agent.logo_url" class="flex-shrink-0">
            <img :src="agent.logo_url" :alt="agent.name" class="w-16 h-16 rounded-xl object-cover" />
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-1">
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ agent.name }}</h1>
              <span v-if="agent.verified" class="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded-full">已验证</span>
            </div>
            <p class="text-gray-500 dark:text-gray-400">{{ agent.agent_id }}</p>
            <div v-if="agent.author" class="text-sm text-gray-400 dark:text-gray-500 mt-1">
              作者: {{ agent.author }}
            </div>
          </div>
        </div>

        <!-- CLI Install -->
        <div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
          <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">CLI 安装</h3>
          <code class="block bg-gray-200 dark:bg-gray-700 rounded px-3 py-2 text-sm font-mono text-gray-800 dark:text-gray-200 overflow-x-auto">
            {{ installCommand }}
          </code>
        </div>

        <!-- Description -->
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">描述</h2>
          <p class="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ agent.description || '暂无描述' }}</p>
        </div>

        <!-- Agent YAML / Parsed Config -->
        <div v-if="agent.parsed_config" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6 space-y-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">配置</h2>

          <!-- System Prompt -->
          <div v-if="agent.parsed_config.prompt?.system">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">System Prompt</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 rounded-lg p-4 whitespace-pre-wrap font-mono">{{ agent.parsed_config.prompt.system }}</p>
          </div>

          <!-- Identity -->
          <div v-if="agent.parsed_config.prompt?.identity">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Identity</h3>
            <div class="flex flex-wrap gap-3 text-sm text-gray-600 dark:text-gray-400">
              <span v-if="agent.parsed_config.prompt.identity.role" class="bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-1">Role: {{ agent.parsed_config.prompt.identity.role }}</span>
              <span v-if="agent.parsed_config.prompt.identity.emoji" class="bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-1">Emoji: {{ agent.parsed_config.prompt.identity.emoji }}</span>
              <span v-if="agent.parsed_config.prompt.identity.vibe" class="bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-1">Vibe: {{ agent.parsed_config.prompt.identity.vibe }}</span>
            </div>
          </div>

          <!-- Workflow File -->
          <div v-if="agent.parsed_config.prompt?.workflow_file">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Workflow File</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400 font-mono">{{ agent.parsed_config.prompt.workflow_file }}</p>
          </div>

          <!-- Skills -->
          <div v-if="agent.parsed_config.skills?.length">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Skills</h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="skill in agent.parsed_config.skills"
                :key="skill.name"
                class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm rounded-full"
              >
                {{ skill.name }}
                <span v-if="skill.source" class="text-gray-400 dark:text-gray-500 text-xs ml-1">({{ skill.source }})</span>
              </span>
            </div>
          </div>

          <!-- Tools -->
          <div v-if="agent.parsed_config.tools?.allowed?.length">
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tools</h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="tool in agent.parsed_config.tools.allowed"
                :key="tool"
                class="px-3 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-300 text-sm rounded-full"
              >
                {{ tool }}
              </span>
            </div>
          </div>
        </div>

        <!-- Agent YAML Raw -->
        <div v-if="agent.agent_yaml_content" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Agent YAML</h2>
          <pre class="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 rounded-lg p-4 overflow-x-auto font-mono">{{ agent.agent_yaml_content }}</pre>
        </div>

        <!-- Readme Content -->
        <div v-if="agent.readme_content" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">README</h2>
          <div class="prose dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 text-sm" v-html="renderedContent"></div>
        </div>

        <!-- Subagents -->
        <div v-if="agent.parsed_config?.subagents?.length" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Subagents</h2>
          <SubagentPanel :subagents="agent.parsed_config.subagents" />
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
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.category || '-' }}</dd>
            </div>
            <div v-if="agent.supported_platforms?.length">
              <dt class="text-sm text-gray-500 dark:text-gray-400">平台</dt>
              <dd class="flex flex-wrap gap-1 mt-1">
                <PlatformBadge v-for="platform in agent.supported_platforms" :key="platform" :platform="platform" />
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 dark:text-gray-400">来源</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.source }}</dd>
            </div>
            <div v-if="agent.source_url">
              <dt class="text-sm text-gray-500 dark:text-gray-400">仓库</dt>
              <dd>
                <a
                  :href="agent.source_url"
                  target="_blank"
                  rel="noopener"
                  class="text-sm text-primary-500 hover:text-primary-600 dark:text-primary-400 dark:hover:text-primary-300 break-all"
                >
                  {{ agent.source_url }}
                </a>
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 dark:text-gray-400">下载量</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.download_count.toLocaleString() }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 dark:text-gray-400">星级</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.star_count.toLocaleString() }}</dd>
            </div>
            <div v-if="agent.license">
              <dt class="text-sm text-gray-500 dark:text-gray-400">许可证</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.license }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 dark:text-gray-400">版本</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.version || '-' }}</dd>
            </div>
            <div v-if="agent.commit_id">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Commit</dt>
              <dd class="font-medium text-gray-900 dark:text-white font-mono text-xs">{{ agent.commit_id }}</dd>
            </div>
            <div v-if="agent.security_score !== null">
              <dt class="text-sm text-gray-500 dark:text-gray-400">安全评分</dt>
              <dd>
                <span
                  class="px-2 py-0.5 text-xs font-medium rounded"
                  :class="{
                    'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300': agent.security_score >= 80,
                    'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300': agent.security_score >= 60 && agent.security_score < 80,
                    'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300': agent.security_score < 60
                  }"
                >
                  {{ agent.security_score }}
                </span>
              </dd>
            </div>
          </dl>
        </div>

        <!-- Tags -->
        <div v-if="agent.tags?.length" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">标签</h2>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="tag in agent.tags"
              :key="tag"
              class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm rounded-full"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- Versions -->
        <div v-if="versions.length" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">版本历史</h2>
          <div class="space-y-2">
            <div
              v-for="ver in versions"
              :key="ver.version"
              class="text-sm"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium text-gray-900 dark:text-white">{{ ver.version }}</span>
                <span class="text-gray-400 dark:text-gray-500 text-xs">{{ ver.download_count.toLocaleString() }} 下载</span>
              </div>
              <div v-if="ver.message" class="text-gray-500 dark:text-gray-400 text-xs mt-0.5">{{ ver.message }}</div>
              <div v-if="ver.released_at" class="text-gray-400 dark:text-gray-500 text-xs">{{ ver.released_at }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
