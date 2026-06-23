<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { Agent, AgentVersion } from '@/api/types'
import PlatformBadge from '@/components/PlatformBadge.vue'
import SubagentPanel from '@/components/SubagentPanel.vue'
import { marked } from 'marked'

const route = useRoute()
const agent = ref<Agent | null>(null)
const versions = ref<AgentVersion[]>([])
const loading = ref(true)
const error = ref('')
const systemPromptExpanded = ref(false)
const SYSTEM_PROMPT_LINES = 20

onMounted(async () => {
  const path = route.params.path as string
  loading.value = true
  try {
    if (path) {
      agent.value = await api.getAgent(path)
      const versionsRes = await api.getAgentVersions(path)
      versions.value = versionsRes.versions || []
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load agent'
  } finally {
    loading.value = false
  }
})

function getSourceName(source: string): string {
  switch (source) {
    case 'github': return 'GitHub'
    case 'gitcode': return 'GitCode'
    default: return source
  }
}

function renderMarkdown(text: string | null): string {
  if (!text) return ''
  return marked(text) as string
}

function getSystemPromptLineCount(text: string | null): number {
  if (!text) return 0
  return text.split('\n').length
}

function shouldCollapseSystemPrompt(text: string | null): boolean {
  return getSystemPromptLineCount(text) > SYSTEM_PROMPT_LINES
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

    <div v-else-if="agent" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Left Column - Main Info (2/3) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Header -->
        <div class="flex items-start gap-4">
          <img
            v-if="agent.logo_url"
            :src="agent.logo_url"
            :alt="agent.name"
            class="w-16 h-16 rounded-lg object-cover"
          />
          <div v-else class="w-16 h-16 rounded-lg bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-2xl">
            🤖
          </div>
          <div>
            <div class="flex items-center gap-3 mb-1">
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ agent.name }}</h1>
              <span v-if="agent.verified" class="text-green-500 text-sm">✓ Verified</span>
            </div>
            <p class="text-gray-500 dark:text-gray-400">{{ agent.agent_id }}</p>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex flex-wrap gap-3">
          <a
            :href="`/api/v1/agents/${encodeURIComponent(agent.agent_id)}/download`"
            target="_blank"
            class="btn-primary"
          >
            📦 Download Agent
          </a>
          <a
            :href="agent.source_url"
            target="_blank"
            rel="noopener"
            class="btn-secondary"
          >
            🌐 Browse Repository
          </a>
          <a
            v-if="agent.homepage_url"
            :href="agent.homepage_url"
            target="_blank"
            rel="noopener"
            class="btn-secondary"
          >
            🏠 Homepage
          </a>
        </div>

        <!-- Description -->
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Description</h2>
          <p class="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ agent.description || 'No description' }}</p>
        </div>

        <!-- Configuration -->
        <div v-if="agent.parsed_config" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Configuration</h2>
          <div class="space-y-4">
            <!-- System Prompt -->
            <div v-if="agent.parsed_config.prompt?.system">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">System Prompt</h3>
                <button
                  v-if="shouldCollapseSystemPrompt(agent.parsed_config.prompt.system)"
                  @click="systemPromptExpanded = !systemPromptExpanded"
                  class="text-xs text-primary-500 hover:text-primary-600 dark:text-primary-400"
                >
                  {{ systemPromptExpanded ? '收起 ▲' : '展开 ▼' }}
                </button>
              </div>
              <div
                class="prose dark:prose-invert max-w-none text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto"
                :class="{ 'max-h-96 overflow-y-auto': shouldCollapseSystemPrompt(agent.parsed_config.prompt.system) && !systemPromptExpanded }"
                v-html="systemPromptExpanded || !shouldCollapseSystemPrompt(agent.parsed_config.prompt.system) ? renderMarkdown(agent.parsed_config.prompt.system) : renderMarkdown(agent.parsed_config.prompt.system.split('\n').slice(0, SYSTEM_PROMPT_LINES).join('\n') + '\n\n...')"
              ></div>
            </div>

            <!-- Identity -->
            <div v-if="agent.parsed_config.prompt?.identity">
              <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Identity</h3>
              <div class="flex items-center gap-3">
                <span class="text-2xl">{{ agent.parsed_config.prompt.identity.emoji || '🤖' }}</span>
                <span v-if="agent.parsed_config.prompt.identity.role" class="text-gray-600 dark:text-gray-300">
                  {{ agent.parsed_config.prompt.identity.role }}
                </span>
                <span v-if="agent.parsed_config.prompt.identity.vibe" class="text-gray-500 dark:text-gray-400 text-sm">
                  ({{ agent.parsed_config.prompt.identity.vibe }})
                </span>
              </div>
            </div>

            <!-- Skills -->
            <div v-if="agent.parsed_config.skills?.length">
              <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Skills</h3>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="skill in agent.parsed_config.skills"
                  :key="skill.name"
                  class="px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded dark:bg-blue-900 dark:text-blue-300"
                >
                  {{ skill.name }}
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
                  class="px-2 py-1 bg-green-100 text-green-700 text-sm rounded dark:bg-green-900 dark:text-green-300 font-mono"
                >
                  {{ tool }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Subagents -->
        <div v-if="agent.parsed_config?.subagents?.length" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Subagents</h2>
          <div class="space-y-3">
            <SubagentPanel
              v-for="subagent in agent.parsed_config.subagents"
              :key="subagent.name"
              :subagent="subagent"
            />
          </div>
        </div>
      </div>

      <!-- Right Column - Sidebar (1/3) -->
      <div class="lg:col-span-1 space-y-6">
        <!-- Meta -->
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Info</h2>
          <dl class="space-y-3">
            <div v-if="agent.category">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Category</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.category }}</dd>
            </div>
            <div v-if="agent.supported_platforms?.length">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Platforms</dt>
              <dd class="flex flex-wrap gap-1 mt-1">
                <PlatformBadge
                  v-for="platform in agent.supported_platforms"
                  :key="platform"
                  :platform="platform"
                />
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 dark:text-gray-400">Source</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ getSourceName(agent.source) }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 dark:text-gray-400">Downloads</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.download_count.toLocaleString() }}</dd>
            </div>
            <div v-if="agent.star_count > 0">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Stars</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.star_count.toLocaleString() }}</dd>
            </div>
            <div v-if="agent.contributor_count > 0">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Contributors</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.contributor_count }}</dd>
            </div>
            <div v-if="agent.license">
              <dt class="text-sm text-gray-500 dark:text-gray-400">License</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.license }}</dd>
            </div>
            <div v-if="agent.version">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Version</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ agent.version }}</dd>
            </div>
            <div v-if="agent.latest_commit_id">
              <dt class="text-sm text-gray-500 dark:text-gray-400">Latest Commit</dt>
              <dd class="font-medium text-gray-900 dark:text-white font-mono text-xs">{{ agent.latest_commit_id.slice(0, 7) }}</dd>
            </div>
          </dl>
        </div>

        <!-- Tags -->
        <div v-if="agent.tags?.length" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Tags</h2>
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

        <!-- Version History -->
        <div v-if="versions.length > 1" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Version History</h2>
          <div class="space-y-2">
            <div
              v-for="v in versions.slice(0, 10)"
              :key="v.version"
              class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="font-medium text-gray-900 dark:text-white">{{ v.version }}</span>
                <span v-if="v.download_count > 0" class="text-xs text-gray-500">
                  ⬇ {{ v.download_count }}
                </span>
              </div>
              <div v-if="v.commit_id" class="text-xs text-gray-400 font-mono">{{ v.commit_id.slice(0, 7) }}</div>
              <div v-if="v.message" class="text-gray-600 dark:text-gray-300 mt-1 truncate">{{ v.message }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
