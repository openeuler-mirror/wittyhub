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
import { OSelect, OOption, OTab, OTabPane, OBreadcrumb, OBreadcrumbItem } from '@opensig/opendesign'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const categoryNames: Record<string, string> = {
  Frontend: '前端',
  Networking: '网络',
  Database: '数据库',
  AI: 'AI',
  Mobile: '移动端',
  DevOps: 'DevOps',
  Backend: '后端',
  Data: '数据',
  Development: '开发工具',
  Design: '设计',
  Cloud: '云服务',
  Security: '安全'
}

const skill = ref<Skill | null>(null)
const versions = ref<SkillVersion[]>([])
const loading = ref(true)
const error = ref('')
const activeTab = ref<'versions' | 'usage'>('usage')
const downloading = ref(false)
const toastVisible = ref(false)

function showCopyToast() {
  toastVisible.value = true
  setTimeout(() => { toastVisible.value = false }, 2000)
}
const selectedVersion = ref<string>('')

function stripFrontmatter(content: string): string {
  const match = content.match(/^---\n[\s\S]*?\n---\n?/)
  if (match) {
    return content.slice(match[0].length).trim()
  }
  return content
}

const renderedContent = computed(() => {
  if (!skill.value?.content) return ''
  const renderer = new marked.Renderer()
  renderer.code = (code: string, lang: string | undefined) => {
    const langClass = lang ? ` class="language-${lang}"` : ''
    const escaped = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    return `<div class="code-block-wrap">
  <button class="code-copy-btn" data-code="${code.replace(/"/g, '&quot;')}" aria-label="复制代码">${copySvg}</button>
  <pre><code${langClass}>${escaped}</code></pre>
</div>\n`
  }
  return marked(stripFrontmatter(skill.value.content), { renderer })
})

async function copyMarkdownCode(e: MouseEvent) {
  const btn = (e.target as HTMLElement).closest('.code-copy-btn') as HTMLElement
  if (!btn) return
  const code = btn.dataset.code
  if (!code) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(code)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = code
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    showCopyToast()
  } catch (e) {
    console.error('复制代码失败:', e)
  }
}

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
    showCopyToast()
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
    showCopyToast()
  } catch (e) {
    console.error('复制失败:', e)
  }
}

async function downloadSkill() {
  if (!skill.value || downloading.value) return
  downloading.value = true
  try {
    const { blob, filename } = await api.getSkillDownload(skill.value.skill_id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
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
        <!-- 复制成功提示 -->
        <transition name="toast">
          <div v-if="toastVisible" class="copy-toast">
            <span class="toast-icon" v-html="checkSvg"></span>
            <span class="toast-text">复制成功</span>
          </div>
        </transition>
        <!-- 面包屑 -->
        <div class="breadcrumb-wrap">
          <OBreadcrumb
            style="
              --breadcrumb-text-size: 14px;
              --breadcrumb-text-height: 22px;
              --breadcrumb-separator-size: 24px;
              --breadcrumb-color: #00000099;
              --breadcrumb-gap: 4px;
            "
          >
            <OBreadcrumbItem to="/">SkillHub</OBreadcrumbItem>
            <OBreadcrumbItem v-if="skill">{{ skill.name }}</OBreadcrumbItem>
            <OBreadcrumbItem v-else>Skill 详情</OBreadcrumbItem>
          </OBreadcrumb>
        </div>

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
              <span v-if="skill.category" class="tag tag-category">{{ categoryNames[skill.category] || skill.category }}</span>
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
            <OTab
              v-model="activeTab"
              variant="button"
              round="4px"
              size="large"
              header-class="detail-tab"
            >
              <OTabPane value="usage" label="使用描述" />
              <OTabPane value="versions" label="版本信息" />
            </OTab>

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
              <div class="markdown-body" v-html="renderedContent" @click="copyMarkdownCode"></div>
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
                <div v-for="v in versions" :key="v.version" class="version-row">
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
              <span>{{ downloading ? '下载中...' : '下载ZIP包安装' }}</span>
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
  max-width: 1488px;
  margin: 0 auto;
  padding: 0 24px;
}



/* ===== Hero 背景区 ===== */
.hero-section {
  position: relative;
  overflow: hidden;
  padding-bottom: 32px;
}

/* ===== 面包屑 ===== */
.breadcrumb-wrap {
  margin-top: 40px;
  margin-bottom: 40px;

  :deep(.o-breadcrumb-item-label) {
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    letter-spacing: 0px;
    text-align: left;
  }
}

/* ===== 加载 & 错误 ===== */
.loading-section {
  padding: 40px 0;
}

.skeleton {
  background: var(--o-color-fill3);
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
    font-size: var(--o-r-font_size-text1);
  }
}

/* ===== 顶部信息卡片 ===== */
.info-card-hero {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 24px;

  .skill-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .skill-name {
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-medium);
    font-size: var(--o-r-font_size-h2);
    line-height: var(--o-r-line_height-h2);
    letter-spacing: 0px;
    text-align: left;
    color: var(--o-color-info1);
    margin-bottom: 0;
  }

  .skill-desc {
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    font-size: 16px;
    line-height: var(--o-r-line_height-text1);
    letter-spacing: 0px;
    text-align: left;
    color: var(--o-color-info3);
    margin-bottom: 16px;
  }

  .tag-category {
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    font-size: 12px;
    line-height: 18px;
    letter-spacing: 0px;
    text-align: left;
    color: var(--o-color-info1);
  }

  .tag-gray {
    border-radius: 4px;
    border: 1px solid var(--o-color-control4);
    background: var(--o-color-fill2);
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    font-size: 12px;
    line-height: 18px;
    letter-spacing: 0px;
    text-align: left;
    color: var(--o-color-info1);
  }

  .skill-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }
}

/* ===== 主体区域（Tab + 右侧卡片） ===== */
.detail-body {
  display: flex;
  gap: 32px;
  align-items: stretch;

  .detail-body-main {
    flex: 1;
    min-width: 0;
  }

  .detail-body-sidebar {
    width: 440px;
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
  margin-bottom: 32px;
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
  font-size: var(--o-font_size-text1);
  font-weight: var(--o-font_weight-regular);
  line-height: var(--o-line_height-text1);
  color: var(--o-color-info1);
  white-space: nowrap;
}

/* OSelect：与筛选栏统一 */
:deep(.o-select) {
  --select-height: 32px;
  --select-radius: 4px;
  --select-text-size: 14px;
  width: 120px;
}

:deep(.o-select-input) {
  font-size: var(--o-font_size-text1);
  font-weight: var(--o-font_weight-regular);
  line-height: var(--o-line_height-text1);
  color: var(--o-color-info1);
}

.action-card {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 20px;
}

.info-card-title {
  font-size: var(--o-font_size-h3);
  font-weight: var(--o-font_weight-medium);
  line-height: var(--o-line_height-h3);
  color: var(--o-color-info1);
  margin: 0;
}

.info-divider {
  height: 1px;
  background: var(--o-color-control4);
  margin: 24px 0;
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
  font-size: var(--o-font_size-text1);
  font-weight: var(--o-font_weight-regular);
  line-height: var(--o-line_height-text2);
  color: var(--o-color-info3);
  white-space: nowrap;
  flex-shrink: 0;
}

.info-value {
  font-size: var(--o-font_size-text1);
  font-weight: var(--o-font_weight-regular);
  line-height: var(--o-line_height-text1);
  color: var(--o-color-info1);
  text-align: left;
  word-break: break-all;
  min-width: 0;
}

.info-link {
  color: var(--o-color-link1);
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular, 400);
  font-size: var(--o-font_size-text1);
  line-height: var(--o-line_height-text1);
  letter-spacing: 0px;
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
  border-radius: 100px;
  font-size: var(--o-r-font_size-tip1);
  font-weight: var(--o-font_weight-medium);
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
  gap: 24px;

  .cli-label {
    font-size: var(--o-font_size-h3);
    font-weight: var(--o-font_weight-medium);
    line-height: var(--o-line_height-h3);
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
    background: var(--o-color-fill3);
    border: none;
    border-radius: 6px;
    overflow: hidden;
  }

  .cli-command {
    flex: 1;
    height: 40px;
    display: flex;
    align-items: center;
    padding: 0 12px;
    font-size: 13px;
    font-family: var(--o-font_family-code);
    color: var(--o-color-info1);
    background: var(--o-color-fill3);
    word-break: keep-all;
    white-space: nowrap;
    overflow-x: auto;

    &::-webkit-scrollbar {
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--o-color-control4);
      border-radius: 3px;
    }
  }

  .cli-copy-btn {
    width: 24px;
    height: 24px;
    margin-right: 12px;
    color: var(--o-color-info3);
    cursor: pointer;
    transition: color 0.2s;
    flex-shrink: 0;

    @include hover {
      color: var(--o-color-primary1);
    }
  }
}

/* ===== Tab 导航 (OTab button variant) ===== */
.detail-tab {
  :deep(.o-tab-head) {
    background: var(--o-color-fill1);
    border-radius: 4px;
    padding: 4px;
    height: 48px;
    border: none;
    box-sizing: border-box;
  }

  :deep(.o-tab-navs) {
    gap: 0;
  }

  :deep(.o-tab-nav) {
    height: 40px;
    padding: 0 16px;
    border: none !important;
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    font-size: var(--o-r-font_size-text2);
    line-height: var(--o-r-line_height-text2);
    letter-spacing: 0;
    color: var(--o-color-info2) !important;
    border-radius: 4px !important;
    background: transparent !important;
    justify-content: center;
    align-items: center;

    &:hover:not(.is-active) {
      background: color-mix(in srgb, var(--o-color-primary1) 8%, transparent);
    }

    &.is-active {
      font-weight: var(--o-font_weight-semibold);
      color: var(--o-color-primary1) !important;
      background: var(--o-color-fill2) !important;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    }
  }
}

/* ===== Tab 内容区 ===== */
.tab-content {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 24px;
  min-height: 200px;
}

/* ===== 版本列表卡片 ===== */
.version-list-card {
  display: flex;
  flex-direction: column;
}

.version-list-title {
  font-size: var(--o-r-font_size-h2);
  font-weight: var(--o-font_weight-semibold);
  color: var(--o-color-info1);
  margin: 0 0 32px;
}

.version-list-divider {
  height: 1px;
  background: var(--o-color-control4);
  margin: 0 0 32px;
}

.version-list-header {
  display: flex;
  align-items: center;
  gap: 40px;
  height: 38px;
  padding: 0 4px;

  .header-label {
    font-size: var(--o-font_size-tip1);
    color: var(--o-color-info1);
    opacity: 0.8;
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-semibold);
    line-height: var(--o-line_height-tip1);

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
  height: 40px;
  background: var(--o-color-fill3);
  border: none;
  border-radius: 6px;
  overflow: hidden;
}

.version-install-cmd {
  flex: 1;
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 13px;
  font-family: var(--o-font_family-code);
  color: var(--o-color-info1);
  background: var(--o-color-fill3);
  word-break: keep-all;
  white-space: nowrap;
  overflow-x: auto;

  &::-webkit-scrollbar {
    height: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--o-color-control4);
    border-radius: 3px;
  }
}

.version-copy-btn {
  width: 24px;
  height: 24px;
  margin: 12px 12px 12px 0;
  color: var(--o-color-info3);
  cursor: pointer;
  transition: color 0.2s;
  flex-shrink: 0;

  @include hover {
    color: var(--o-color-primary1);
  }
}

.version-badge {
  display: inline-block;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-r-font_size-tip1);
  line-height: var(--o-r-line_height-tip1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info1);
  padding: 2px 0;
  white-space: nowrap;
  flex-shrink: 0;
  width: 100px;
}

.version-header-divider {
  height: 1px;
  background: var(--o-color-primary1);
  border-radius: 1px;
  margin: 0;
}

.version-rows {
  display: flex;
  flex-direction: column;
}

.version-row {
  display: flex;
  align-items: center;
  gap: 40px;
  height: 56px;
  padding: 0 4px;
  border-bottom: 1px solid var(--o-color-control4);

  &:last-child {
    border-bottom: none;
  }
}

/* ===== 使用描述 ===== */
.usage-content {
  line-height: 1.8;
}

.markdown-body {
  color: var(--o-color-info1);
  font-size: 15px;
  line-height: 1.8;

  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    margin-top: 24px;
    margin-bottom: 12px;
    color: var(--o-color-info1);
    font-weight: 600;
  }

  :deep(h1) { font-size: 32px; }
  :deep(h2) { font-size: 24px; }
  :deep(h3) { font-size: 20px; }
  :deep(h4) { font-size: 15px; }
  :deep(h5) { font-size: 14px; }
  :deep(h6) { font-size: 13px; }

  :deep(p) {
      margin-bottom: 14px;
      color: var(--o-color-info2);
      font-size: 16px;
    }

  :deep(ul) {
    margin-bottom: 14px;
    padding-left: 24px;
    color: var(--o-color-info2);
    list-style: disc;
  }

  :deep(ol) {
    margin-bottom: 14px;
    padding-left: 24px;
    color: var(--o-color-info2);
    list-style: decimal;
  }

  :deep(li) {
    margin-bottom: 6px;
    font-size: 16px;
  }

  :deep(code) {
    font-family: var(--o-font_family-code);
    font-size: 14px;
    background: var(--o-color-fill1);
    padding: 2px 8px;
    border-radius: 4px;
    color: var(--o-color-info2);
  }

  :deep(pre) {
    background: var(--o-color-fill1);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    margin-bottom: 16px;

    &::-webkit-scrollbar {
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--o-color-control4);
      border-radius: 3px;
    }

    code {
      background: none;
      padding: 0;
      color: var(--o-color-info1);
      font-size: 14px;
    }
    font-size: 14px;
  }

  :deep(blockquote) {
    border-left: 3px solid var(--o-color-primary1);
    padding-left: 16px;
    margin-left: 0;
    margin-bottom: 14px;
    color: var(--o-color-info3);
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
      color: var(--o-color-info2);
    }

    td {
      color: var(--o-color-info2);
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

  /* ===== 代码块复制按钮 ===== */
  :deep(.code-block-wrap) {
    position: relative;
  }

  :deep(.code-copy-btn) {
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: transparent;
    border: none;
    color: var(--o-color-info3);
    cursor: pointer;
    opacity: 1;
    transition: color 0.2s;

    @include hover {
      color: var(--o-color-primary1);
    }

    &:active {
      opacity: 1;
    }

    &.is-copied {
      color: var(--o-color-success1);
      cursor: default;
      opacity: 1;
      border-color: var(--o-color-success1);
    }

    :deep(svg) {
      width: 12px;
      height: 12px;
    }
  }
}

/* ===== 空态 ===== */
.empty-tab {
  text-align: center;
  padding: 48px 0;
  color: var(--o-color-info3);

  .empty-hint {
    margin-top: 8px;
    font-size: 13px;
    color: var(--o-color-info4);
  }
}

/* ===== 响应式 ===== */
@include respond-to('<=pad_v') {
  .detail-page {
    padding-bottom: 40px;
  }

  .hero-section {
    padding-bottom: 20px;
  }

  .container-wide {
    padding: 0 16px;
  }

  .info-card-hero {
    padding: 24px;

    .skill-name {
      font-size: 24px;
      line-height: 32px;
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

  .cli-section {
    flex-direction: column;
    align-items: stretch;

    .cli-input-group {
      flex-direction: column;

      .cli-command {
        height: 40px;
        padding: 0 12px;
      }

      .cli-copy-btn {
        justify-content: center;
        padding: 8px;
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
    height: auto;
    padding: 10px 0;
  }
}
</style>

<style scoped>
/* ===== 复制提示 Toast ===== */
.copy-toast {
  position: fixed;
  top: 96px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: var(--o-radius-s);
  background: var(--o-color-fill2);
  box-shadow: var(--o-shadow-2);
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;

  :deep(svg) {
    width: 24px;
    height: 24px;
  }

  :deep(rect) {
    fill: #0BB151;
  }
}

.toast-text {
  color: var(--o-color-info1);
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-r-font_size-text1);
  line-height: var(--o-r-line_height-text1);
  letter-spacing: 0;
  text-align: left;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-12px);
}
</style>
