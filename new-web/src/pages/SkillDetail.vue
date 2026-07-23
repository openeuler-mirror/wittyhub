<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Skill, SkillVersion } from '@/api/types'
import { marked } from 'marked'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'
import copySvg from '@/assets/icons/copy.svg?raw'
import checkSvg from '@/assets/icons/check.svg?raw'
import downloadSvg from '@/assets/icons/download.svg?raw'
import { OSelect, OOption } from '@opensig/opendesign'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const skill = ref<Skill | null>(null)
const versions = ref<SkillVersion[]>([])
const loading = ref(true)
const error = ref('')
const activeTab = ref<'versions' | 'usage'>('usage')
const cliCopied = ref(false)
const downloading = ref(false)
const selectedVersion = ref<string>('')
const copiedVersion = ref(false)

function stripFrontmatter(content: string): string {
  const match = content.match(/^---\n[\s\S]*?\n---\n?/)
  if (match) {
    return content.slice(match[0].length).trim()
  }
  return content
}

const renderedContent = computed(() => {
  if (!skill.value?.content) return ''
  return marked(stripFrontmatter(skill.value.content))
})

const filteredVersions = computed(() => {
  if (!selectedVersion.value) return versions.value
  return versions.value.filter(v => v.version === selectedVersion.value)
})

function getSecurityLevel(score: number | null): { label: string; class: string } {
  if (score === null) return { label: '未检测', class: 'tag-gray' }
  if (score <= 20) return { label: '安全', class: 'tag-green' }
  if (score <= 50) return { label: '低风险', class: 'tag-blue' }
  if (score <= 80) return { label: '中风险', class: 'tag-orange' }
  return { label: '高风险', class: 'tag-red' }
}

const securityLevel = computed(() => getSecurityLevel(skill.value?.risk_score ?? null))

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hh}:${mm}`
}

function truncateHash(hash: string | null): string {
  if (!hash) return '-'
  return hash.length > 8 ? hash.slice(0, 8) : hash
}

async function copyCliCommand() {
  if (!skill.value) return
  const command = `npx wittyhub install ${skill.value.skill_id}`
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(command)
    } else {
      // fallback for HTTP contexts
      const textarea = document.createElement('textarea')
      textarea.value = command
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    cliCopied.value = true
    setTimeout(() => { cliCopied.value = false }, 3000)
  } catch (e) {
    console.error('复制失败:', e)
  }
}

function copyVersionCmd(skillId: string) {
  const command = `npx wittyhub install ${skillId}`
  try {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(command)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = command
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copiedVersion.value = true
    setTimeout(() => { copiedVersion.value = false }, 3000)
  } catch (e) {
    console.error('复制失败:', e)
  }
}

async function downloadSkill() {
  if (!skill.value || downloading.value) return
  downloading.value = true
  try {
    const resp = await api.getSkillDownload(skill.value.skill_id)
    if (resp.download_url) {
      window.open(resp.download_url, '_blank')
    }
  } catch (e) {
    console.error('下载失败:', e)
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  const skillId = route.params.skillId as string
  if (!skillId) {
    error.value = '缺少 Skill ID'
    loading.value = false
    return
  }
  loading.value = true
  try {
    const [skillRes, versionsRes] = await Promise.all([
      api.getSkill(decodeURIComponent(skillId)),
      api.getSkillVersions(decodeURIComponent(skillId))
    ])
    skill.value = skillRes
    versions.value = versionsRes.versions || []
    if (versions.value.length > 0) {
      selectedVersion.value = versions.value[0].version
    }
  } catch (e: any) {
    console.error('加载 Skill 详情失败:', e)
    error.value = e?.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="detail-page">
    <!-- ========== Hero 区域 ========== -->
    <section class="hero-section">
      <div class="absolute inset-0 pointer-events-none">
        <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" class="w-full h-full object-cover" />
      </div>
      <div class="container-wide relative flex flex-col">
        <!-- 面包屑 -->
        <nav class="breadcrumb">
          <a href="/" class="breadcrumb-link" @click.prevent="router.push('/')">首页</a>
          <span class="breadcrumb-sep">›</span>
          <span class="breadcrumb-current" v-if="skill">{{ skill.name }}</span>
          <span class="breadcrumb-current" v-else>Skill 详情</span>
        </nav>

        <!-- 加载态 -->
        <div v-if="loading" class="loading-section">
          <div class="skeleton h-8 w-1/2 mb-4"></div>
          <div class="skeleton h-4 w-1/3 mb-6"></div>
          <div class="skeleton h-24 w-full mb-8"></div>
          <div class="skeleton h-48 w-full"></div>
        </div>

        <!-- 错误态 -->
        <div v-else-if="error" class="error-section">
          <p class="error-text">{{ error }}</p>
        </div>

        <!-- 正常显示 -->
        <template v-else-if="skill">
          <!-- ========== 顶部信息卡片 ========== -->
          <div class="info-card-hero">
            <div class="skill-title-row">
              <h1 class="skill-name">{{ skill.name }}</h1>
              <span :class="['tag', securityLevel.class]">{{ securityLevel.label }}</span>
            </div>
            <p class="skill-desc" v-if="skill.description">{{ skill.description }}</p>

            <!-- 标签区 -->
            <div class="skill-tags">
              <span v-if="skill.category" class="tag tag-blue">{{ skill.category }}</span>
              <span v-if="skill.platform" class="tag tag-gray">{{ skill.platform }}</span>
              <span
                v-for="tag in (skill.tags || []).slice(0, 5)"
                :key="tag"
                class="tag tag-gray"
              >{{ tag }}</span>
            </div>
          </div>
          <!-- end info-card-hero -->
        </template>
      </div>
    </section>

    <div v-if="skill" class="container-wide">
      <div class="detail-body">
        <div class="detail-body-main">
          <!-- ========== Tab 导航 + 筛选 ========== -->
          <div class="tab-header">
            <div class="switch-tab">
              <div
                class="switch-tab-slider"
                :class="{ 'slider-right': activeTab === 'versions' }"
              />
              <button
                class="switch-handler"
                :class="{ active: activeTab === 'usage' }"
                @click="activeTab = 'usage'"
              >
                使用描述
              </button>
              <button
                class="switch-handler"
                :class="{ active: activeTab === 'versions' }"
                @click="activeTab = 'versions'"
              >
                版本信息
              </button>
            </div>

            <!-- 版本筛选栏 -->
            <div class="version-toolbar">
              <div class="version-card">
                <span class="version-card-label">版本</span>
                <OSelect
                  v-model="selectedVersion"
                  size="medium"
                  option-width-mode="width"
                  no-responsive
                >
                  <OOption
                    v-for="v in versions"
                    :key="v.version"
                    :label="v.version"
                    :value="v.version"
                  />
                </OSelect>
              </div>
            </div>
          </div>

          <!-- ========== 使用描述 Tab ========== -->
          <div v-show="activeTab === 'usage'" class="tab-content">
            <div v-if="skill.content" class="usage-content">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div class="markdown-body" v-html="renderedContent"></div>
            </div>
            <div v-else class="empty-tab">
              <p>暂无使用描述</p>
              <p class="empty-hint">内容将在本地安装后显示</p>
            </div>
          </div>

          <!-- ========== 版本信息 Tab ========== -->
          <div v-show="activeTab === 'versions'" class="tab-content">
            <div v-if="versions.length > 0" class="version-list-card">
              <h3 class="version-list-title">版本列表</h3>
              <div class="version-list-divider"></div>
              <div class="version-list-header">
                <span class="header-label">版本</span>
                <span class="header-label">安装命令</span>
              </div>
              <div class="version-header-divider"></div>
              <div class="version-rows">
                <div v-for="v in filteredVersions" :key="v.version" class="version-row">
                  <span class="version-badge">{{ v.version }}</span>
                  <div class="version-cli-group">
                    <code class="version-install-cmd">npx wittyhub install {{ skill?.skill_id }}</code>
                    <button
                      class="version-copy-btn"
                      :class="{ 'is-copied': copiedVersion }"
                      aria-label="复制"
                      @click="copyVersionCmd(skill?.skill_id ?? '')"
                    >
                      <span v-if="!copiedVersion" class="btn-icon-sm" v-html="copySvg"></span>
                      <span v-else class="btn-icon-sm copied-icon">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <circle cx="12" cy="12" r="10" fill="currentColor"/>
                          <path d="M8 12l3 3 5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="empty-tab">
              <p>暂无版本信息</p>
            </div>
          </div>
        </div>

        <!-- ========== 右侧：CLI 安装独立卡片 ========== -->
        <aside class="detail-body-sidebar">
          <div class="sidebar-sticky">
            <div class="action-card">
              <div class="cli-section">
                <h3 class="cli-label">CLI 安装</h3>
                <div class="cli-divider"></div>
                <div class="cli-input-group">
                  <code class="cli-command">npx wittyhub install {{ skill.skill_id }}</code>
                  <button class="cli-copy-btn" :class="{ 'is-copied': cliCopied }" @click="copyCliCommand" :aria-label="cliCopied ? '已复制' : '复制'">
                    <span v-if="!cliCopied" class="btn-icon-sm" v-html="copySvg"></span>
                    <span v-else class="btn-icon-sm copied-icon">
                      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="12" cy="12" r="10" fill="currentColor"/>
                        <path d="M8 12l3 3 5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>
                    </span>
                  </button>
                </div>
              </div>
            </div>

            <!-- 下载按钮 -->
            <button class="download-btn" :disabled="downloading" @click="downloadSkill">
              <span class="download-btn-icon" v-html="downloadSvg"></span>
              <span>{{ downloading ? '下载中...' : '下载 ZIP' }}</span>
            </button>

            <!-- Skill 信息卡片 -->
            <div class="info-card">
              <h3 class="info-card-title">Skill 信息</h3>
              <div class="info-divider"></div>
              <div class="info-list">
                <div class="info-row">
                  <span class="info-label">贡献者</span>
                  <span class="info-value">{{ skill.author || '-' }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">仓库地址</span>
                  <a v-if="skill.source_url" :href="skill.source_url" target="_blank" class="info-link" rel="noopener noreferrer">{{ skill.source_url }}</a>
                  <span v-else class="info-value">-</span>
                </div>
                <div class="info-row">
                  <span class="info-label">下载量</span>
                  <span class="info-value">{{ skill.download_count.toLocaleString() }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">更新时间</span>
                  <span class="info-value">{{ formatDate(skill.updated_at) }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">版本</span>
                  <span class="info-value">{{ skill.version || '-' }}</span>
                </div>
              </div>
            </div>
          </div>
          <!-- end sidebar-sticky -->
        </aside>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.container-wide {
  max-width: 1416px;
  margin: 0 auto;
  padding: 0 24px;
}

.detail-page {
  padding-bottom: 64px;
}

/* ===== Hero 背景区 ===== */
.hero-section {
  position: relative;
  overflow: hidden;
  padding-bottom: 32px;

  .breadcrumb {
    padding-top: 32px;
  }
}

/* ===== 面包屑 ===== */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  font-size: 14px;
  line-height: 22px;

  .breadcrumb-link {
    color: var(--o-color-text3);
    text-decoration: none;
    @include hover { color: var(--o-color-primary1); }
  }

  .breadcrumb-sep {
    color: var(--o-color-text4);
    font-size: 18px;
    line-height: 1;
  }

  .breadcrumb-current {
    color: var(--o-color-primary1);
  }
}

/* ===== 加载 & 错误 ===== */
.loading-section {
  padding: 40px 0;
}

.skeleton {
  background: var(--o-color-control6);
  border-radius: 8px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.error-section {
  text-align: center;
  padding: 80px 0;
  .error-text {
    color: var(--o-color-danger1);
    font-size: 16px;
  }
}

/* ===== 顶部信息卡片 ===== */
.info-card-hero {
  background: var(--o-color-fill2);
  border: 1px solid var(--o-color-control4);
  border-radius: 8px;
  padding: 32px;

  .skill-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .skill-name {
    font-size: 28px;
    font-weight: 700;
    line-height: 38px;
    color: var(--o-color-info1);
  }

  .skill-desc {
    font-size: 15px;
    line-height: 24px;
    color: var(--o-color-text2);
    margin-bottom: 16px;
  }

  .skill-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }

  .skill-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--o-color-text3);
    }

    .meta-icon {
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }
  }
}

/* ===== 主体区域（Tab + 右侧卡片） ===== */
.detail-body {
  display: flex;
  gap: 24px;
  align-items: stretch;

  .detail-body-main {
    flex: 1;
    min-width: 0;
  }

  .detail-body-sidebar {
    width: 448px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }
}

.sidebar-sticky {
  position: sticky;
  top: 96px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  min-height: 36px;
}

.version-toolbar {
  display: flex;
  align-items: center;
  min-height: 30px;
}

.version-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.version-card-label {
  font-size: 13px;
  color: var(--o-color-text3);
  white-space: nowrap;
  line-height: 32px;
}

/* OSelect：与 switch-tab/筛选栏统一 */
:deep(.o-select) {
  --select-height: 32px;
  --select-radius: 4px;
  --select-text-size: 14px;
  width: 120px;
}

.action-card {
  background: var(--o-color-fill2);
  border: 1px solid var(--o-color-control4);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: var(--o-color-fill2);
  border: 1px solid var(--o-color-control4);
  border-radius: 8px;
  padding: 20px;
}

.info-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--o-color-text1);
  margin: 0;
}

.info-divider {
  height: 1px;
  background: var(--o-color-control4);
  margin: 12px 0;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}

.info-label {
  font-size: 13px;
  color: var(--o-color-text3);
  white-space: nowrap;
  flex-shrink: 0;
}

.info-value {
  font-size: 13px;
  color: var(--o-color-text1);
  text-align: right;
  word-break: break-all;
  min-width: 0;
}

.info-link {
  font-size: 13px;
  color: var(--o-color-link1);
  text-align: right;
  word-break: break-all;
  text-decoration: none;

  @include hover {
    text-decoration: underline;
  }
}

/* ===== 下载按钮 ===== */
.download-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  background: var(--o-color-primary1);
  color: #fff;
  transition: background 0.2s;

  @include hover {
    background: color-mix(in srgb, var(--o-color-primary1) 85%, #000);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .download-btn-icon {
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;

    :deep(svg) {
      width: 18px;
      height: 18px;
    }
  }
}


/* ===== CLI 安装区 ===== */
.cli-section {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .cli-label {
    font-size: 16px;
    font-weight: 600;
    color: var(--o-color-info1);
    margin: 0;
  }

  .cli-divider {
    height: 1px;
    background: var(--o-color-control4);
    margin: 0;
  }

  .cli-input-group {
    display: flex;
    align-items: center;
    background: var(--o-color-fill2);
    border: 1px solid var(--o-color-control4);
    border-radius: 6px;
    overflow: hidden;
  }

  .cli-command {
    flex: 1;
    padding: 8px 12px;
    font-size: 13px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: var(--o-color-info1);
    background: var(--o-color-fill3);
    overflow-x: auto;
    white-space: nowrap;
  }

  .cli-copy-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: transparent;
    color: var(--o-color-text3);
    border: none;
    cursor: pointer;
    transition: color 0.2s;
    flex-shrink: 0;

    @include hover {
      color: var(--o-color-primary1);
    }

    &.is-copied {
      color: var(--o-color-success1, #22c55e);
      cursor: default;
      @include hover { color: var(--o-color-success1, #22c55e); }
    }

    .btn-icon-sm {
      width: 16px;
      height: 16px;
      display: flex;
      align-items: center;
      justify-content: center;

      :deep(svg) {
        width: 16px;
        height: 16px;
      }
    }

    .copied-icon {
      svg {
        width: 20px;
        height: 20px;
      }
    }
  }
}

/* ===== Tab 导航 (switch-tab 样式) ===== */
.switch-tab {
  display: inline-flex;
  position: relative;
  background: var(--o-color-fill1);
  border-radius: 8px;
  padding: 3px;
}

.switch-tab-slider {
  position: absolute;
  width: calc(50% - 2.5px);
  height: calc(100% - 6px);
  top: 3px;
  left: 3px;
  background: var(--o-color-fill2);
  border-radius: 5px;
  z-index: 1;
  transition: left 0.2s cubic-bezier(0.2, 0, 0, 1);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  pointer-events: none;
}

.switch-tab-slider.slider-right {
  left: calc(50% + 0.5px);
}

.switch-handler {
  position: relative;
  z-index: 2;
  padding: 4px 16px;
  height: 30px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--o-color-info1);
  font-size: 14px;
  line-height: 22px;
  border-radius: 5px;
  transition: color 0.2s ease;
  user-select: none;

  @include hover {
    &:not(.active) {
      color: var(--o-color-link1);
      background: var(--o-color-fill3);
    }
  }

  &.active {
    color: var(--o-color-link1);
    font-weight: 500;
  }
}

/* ===== Tab 内容区 ===== */
.tab-content {
  background: var(--o-color-fill2);
  border: 1px solid var(--o-color-control4);
  border-top: none;
  border-radius: 0 0 12px 12px;
  padding: 24px;
  min-height: 200px;
}

/* ===== 版本列表卡片 ===== */
.version-list-card {
  display: flex;
  flex-direction: column;
}

.version-list-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--o-color-info1);
  margin: 0 0 8px;
}

.version-list-divider {
  height: 1px;
  background: var(--o-color-control4);
  margin: 8px 0 12px;
}

.version-list-header {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 0 4px;

  .header-label {
    font-size: 13px;
    color: var(--o-color-text3);
    font-weight: 500;

    &:first-child {
      width: 100px;
      flex-shrink: 0;
    }

    &:last-child {
      flex: 1;
    }
  }
}

.version-cli-group {
  display: flex;
  align-items: center;
  flex: 1;
  background: var(--o-color-fill2);
  border: 1px solid var(--o-color-control4);
  border-radius: 6px;
  overflow: hidden;
}

.version-install-cmd {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--o-color-info1);
  background: var(--o-color-fill3);
  overflow-x: auto;
  white-space: nowrap;
}

.version-copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  color: var(--o-color-text3);
  border: none;
  cursor: pointer;
  transition: color 0.2s;
  flex-shrink: 0;

  @include hover {
    color: var(--o-color-primary1);
  }

  &.is-copied {
    color: var(--o-color-success1, #22c55e);
    cursor: default;
    @include hover { color: var(--o-color-success1, #22c55e); }
  }

  .btn-icon-sm {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;

    :deep(svg) {
      width: 16px;
      height: 16px;
    }
  }

  .copied-icon {
    svg {
      width: 20px;
      height: 20px;
    }
  }
}

.version-badge {
  display: inline-block;
  font-size: 13px;
  font-weight: 500;
  color: var(--o-color-link1);
  padding: 2px 0;
  white-space: nowrap;
  flex-shrink: 0;
  width: 100px;
}

.version-header-divider {
  height: 2px;
  background: var(--o-color-primary1);
  border-radius: 1px;
  margin-bottom: 4px;
}

.version-rows {
  display: flex;
  flex-direction: column;
}

.version-row {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--o-color-control4);

  &:last-child {
    border-bottom: none;
  }
}

/* ===== Tab 内容卡片 ===== */
.tab-content {
  background: var(--o-color-fill2);
  border: 1px solid var(--o-color-control4);
  border-radius: 8px;
  padding: 24px;
}

/* ===== 使用描述 ===== */
.usage-content {
  line-height: 1.8;
}

.markdown-body {
  color: var(--o-color-info1);
  font-size: 15px;
  line-height: 1.8;

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    margin-top: 24px;
    margin-bottom: 12px;
    color: var(--o-color-info1);
    font-weight: 600;
  }

  :deep(h1) { font-size: 24px; }
  :deep(h2) { font-size: 20px; }
  :deep(h3) { font-size: 17px; }

  :deep(p) {
    margin-bottom: 14px;
    color: var(--o-color-text2);
  }

  :deep(ul), :deep(ol) {
    margin-bottom: 14px;
    padding-left: 24px;
    color: var(--o-color-text2);
  }

  :deep(li) {
    margin-bottom: 6px;
  }

  :deep(code) {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 13px;
    background: var(--o-color-fill1);
    padding: 2px 8px;
    border-radius: 4px;
    color: var(--o-color-primary1);
  }

  :deep(pre) {
    background: var(--o-color-fill1);
    border: 1px solid var(--o-color-control4);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    margin-bottom: 16px;

    code {
      background: none;
      padding: 0;
      color: var(--o-color-info1);
    }
  }

  :deep(blockquote) {
    border-left: 3px solid var(--o-color-primary1);
    padding-left: 16px;
    margin-left: 0;
    margin-bottom: 14px;
    color: var(--o-color-text3);
  }

  :deep(a) {
    color: var(--o-color-primary1);
    text-decoration: none;
    @include hover { text-decoration: underline; }
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;

    th, td {
      padding: 10px 14px;
      border: 1px solid var(--o-color-control4);
      text-align: left;
      font-size: 14px;
    }

    th {
      background: var(--o-color-fill1);
      font-weight: 600;
      color: var(--o-color-text2);
    }

    td {
      color: var(--o-color-text2);
    }
  }

  :deep(hr) {
    border: none;
    border-top: 1px solid var(--o-color-control4);
    margin: 20px 0;
  }

  :deep(img) {
    max-width: 100%;
    border-radius: 8px;
  }
}

/* ===== 空态 ===== */
.empty-tab {
  text-align: center;
  padding: 48px 0;
  color: var(--o-color-text3);

  .empty-hint {
    margin-top: 8px;
    font-size: 13px;
    color: var(--o-color-text4);
  }
}

/* ===== 响应式 ===== */
@include respond-to('<=pad_v') {
  .detail-page {
    padding-bottom: 40px;
  }

  .hero-section {
    padding-bottom: 20px;

    .breadcrumb {
      padding-top: 20px;
    }
  }

  .container-wide {
    padding: 0 16px;
  }

  .info-card-hero {
    padding: 20px;

    .skill-name {
      font-size: 22px;
      line-height: 30px;
    }

    .skill-meta {
      gap: 12px;
      flex-direction: column;
    }
  }

  .detail-body {
    flex-direction: column;

    .detail-body-sidebar {
      width: 100%;
    }

    .sidebar-sticky {
      position: static;
    }
  }

  .info-card-actions {
    flex-direction: row;

    .action-btn {
      flex: 1;
      justify-content: center;
    }
  }

  .cli-section {
    flex-direction: column;
    align-items: stretch;

    .cli-input-group {
      flex-direction: column;

      .cli-command {
        padding: 8px 12px;
      }

      .cli-copy-btn {
        justify-content: center;
        padding: 8px;
      }
    }
  }

  .tab-nav {
    .tab-btn {
      padding: 10px 16px;
      font-size: 14px;
      flex: 1;
      text-align: center;
    }

    .tab-indicator {
      width: 50%;

      &.tab-right {
        left: 50%;
      }
    }
  }

  .tab-content {
    padding: 16px;
  }

  .version-row {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
    padding: 10px 0;
  }
}
</style>
