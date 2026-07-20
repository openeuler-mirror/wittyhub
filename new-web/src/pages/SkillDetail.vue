<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Skill, SkillVersion } from '@/api/types'
import { marked } from 'marked'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const skill = ref<Skill | null>(null)
const versions = ref<SkillVersion[]>([])
const loading = ref(true)
const error = ref('')
const activeTab = ref<'versions' | 'usage'>('versions')
const cliCopied = ref(false)

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

function getSecurityLevel(score: number | null): { label: string; class: string } {
  if (score === null) return { label: '未检测', class: 'tag-gray' }
  if (score >= 80) return { label: '安全', class: 'tag-green' }
  if (score >= 50) return { label: '低风险', class: 'tag-blue' }
  if (score >= 20) return { label: '中风险', class: 'tag-orange' }
  return { label: '高风险', class: 'tag-red' }
}

const securityLevel = computed(() => getSecurityLevel(skill.value?.security_score ?? null))

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
  const command = `skillhub install ${skill.value.skill_id}`
  try {
    await navigator.clipboard.writeText(command)
    cliCopied.value = true
    setTimeout(() => { cliCopied.value = false }, 2000)
  } catch (e) {
    console.error('复制失败:', e)
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
          <span class="breadcrumb-sep">/</span>
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
          <div class="info-card-main">
            <div class="info-card-left">
              <div class="skill-title-row">
                <h1 class="skill-name">{{ skill.name }}</h1>
                <span :class="['tag', securityLevel.class]">{{ securityLevel.label }}</span>
              </div>
              <p class="skill-id">{{ skill.skill_id }}</p>
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

              <!-- 元信息行 -->
              <div class="skill-meta">
                <span class="meta-item">
                  <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                  </svg>
                  v{{ skill.version || '-' }}
                </span>
                <span class="meta-item">
                  <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  </svg>
                  {{ skill.author || '-' }}
                </span>
                <span class="meta-item">
                  <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  {{ skill.download_count.toLocaleString() }} 下载
                </span>
                <span class="meta-item">
                  <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                  更新于 {{ formatDate(skill.updated_at) }}
                </span>
                <span class="meta-item">
                  <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
                  </svg>
                  {{ skill.source || '-' }}
                </span>
              </div>
            </div>
          </div>

          <!-- 操作区 -->
          <div class="info-card-actions">
            <a
              v-if="skill.source_url"
              :href="skill.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="action-btn action-btn-primary"
            >
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载 ZIP
            </a>
            <a
              v-if="skill.source_url"
              :href="skill.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="action-btn action-btn-secondary"
            >
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
              </svg>
              浏览仓库
            </a>
          </div>

          <!-- CLI 安装 -->
          <div class="cli-section">
            <span class="cli-label">CLI 安装</span>
            <div class="cli-input-group">
              <code class="cli-command">skillhub install {{ skill.skill_id }}</code>
              <button class="cli-copy-btn" @click="copyCliCommand">
                <svg v-if="!cliCopied" class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                </svg>
                <span v-else class="copied-text">✓</span>
                <span>{{ cliCopied ? '已复制' : '复制' }}</span>
              </button>
            </div>
          </div>
          </div>
          <!-- end info-card-hero -->
        </template>
      </div>
    </section>

    <div v-if="skill" class="container-wide">
        <!-- ========== Tab 导航 ========== -->
        <div class="switch-tab">
          <div
            class="switch-tab-slider"
            :class="{ 'slider-right': activeTab === 'usage' }"
          />
          <button
            class="switch-handler"
            :class="{ active: activeTab === 'versions' }"
            @click="activeTab = 'versions'"
          >
            版本信息
          </button>
          <button
            class="switch-handler"
            :class="{ active: activeTab === 'usage' }"
            @click="activeTab = 'usage'"
          >
            使用描述
          </button>
        </div>

        <!-- ========== 版本信息 Tab ========== -->
        <div v-show="activeTab === 'versions'" class="tab-content">
          <div v-if="versions.length > 0" class="versions-table-wrapper">
            <table class="versions-table">
              <thead>
                <tr>
                  <th>版本号</th>
                  <th>Commit ID</th>
                  <th>作者</th>
                  <th>提交信息</th>
                  <th>发布时间</th>
                  <th>下载量</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="v in versions" :key="v.version">
                  <td>
                    <span class="version-badge">v{{ v.version }}</span>
                  </td>
                  <td>
                    <code class="commit-hash" :title="v.commit_id || ''">{{ truncateHash(v.commit_id) }}</code>
                  </td>
                  <td class="cell-author">{{ v.author || '-' }}</td>
                  <td class="cell-message">{{ v.message || '-' }}</td>
                  <td>{{ formatDate(v.released_at) }}</td>
                  <td class="cell-downloads">{{ v.download_count?.toLocaleString() || 0 }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-tab">
            <p>暂无版本信息</p>
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
    color: var(--o-color-primary1);
    text-decoration: none;
    @include hover { text-decoration: underline; }
  }

  .breadcrumb-sep {
    color: var(--o-color-text4);
  }

  .breadcrumb-current {
    color: var(--o-color-text3);
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

  .info-card-main {
    margin-bottom: 24px;
  }

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

  .skill-id {
    font-size: 13px;
    color: var(--o-color-text4);
    font-family: 'SF Mono', 'Fira Code', monospace;
    margin-bottom: 12px;
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

/* ===== 操作区 ===== */
.info-card-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;

  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn-icon {
    width: 16px;
    height: 16px;
  }

  .action-btn-primary {
    background: var(--o-color-primary1);
    color: #fff;
    @include hover {
      background: color-mix(in srgb, var(--o-color-primary1) 85%, #000);
    }
  }

  .action-btn-secondary {
    background: var(--o-color-fill3);
    color: var(--o-color-info1);
    border: 1px solid var(--o-color-control4);
    @include hover {
      background: var(--o-color-control6);
    }
  }
}

/* ===== CLI 安装区 ===== */
.cli-section {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--o-color-fill1);
  border-radius: 8px;
  padding: 12px 16px;

  .cli-label {
    font-size: 13px;
    color: var(--o-color-text3);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .cli-input-group {
    flex: 1;
    display: flex;
    align-items: center;
    background: var(--o-color-fill2);
    border: 1px solid var(--o-color-control4);
    border-radius: 6px;
    overflow: hidden;
  }

  .cli-command {
    flex: 1;
    padding: 6px 12px;
    font-size: 13px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: var(--o-color-info1);
    overflow-x: auto;
    white-space: nowrap;
  }

  .cli-copy-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 14px;
    background: var(--o-color-primary1);
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.2s;
    white-space: nowrap;
    flex-shrink: 0;

    @include hover {
      background: color-mix(in srgb, var(--o-color-primary1) 85%, #000);
    }

    .btn-icon-sm {
      width: 14px;
      height: 14px;
    }

    .copied-text {
      font-weight: 600;
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
  margin-bottom: 16px;
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

/* ===== 版本信息表格 ===== */
.versions-table-wrapper {
  overflow-x: auto;
}

.versions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;

  thead {
    background: var(--o-color-fill1);

    th {
      padding: 12px 16px;
      text-align: left;
      font-weight: 600;
      color: var(--o-color-text2);
      font-size: 13px;
      white-space: nowrap;
      border-bottom: 1px solid var(--o-color-control4);
    }
  }

  tbody {
    tr {
      border-bottom: 1px solid var(--o-color-control5);
      transition: background 0.15s;

      @include hover {
        background: var(--o-color-fill1);
      }

      &:last-child {
        border-bottom: none;
      }
    }

    td {
      padding: 14px 16px;
      color: var(--o-color-info1);
      font-size: 14px;
    }
  }

  .version-badge {
    display: inline-block;
    padding: 2px 10px;
    background: color-mix(in srgb, var(--o-color-primary1) 12%, transparent);
    color: var(--o-color-primary1);
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .commit-hash {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 12px;
    background: var(--o-color-fill1);
    padding: 2px 8px;
    border-radius: 4px;
    color: var(--o-color-text3);
  }

  .cell-author {
    color: var(--o-color-text2);
  }

  .cell-message {
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--o-color-text2);
  }

  .cell-downloads {
    font-variant-numeric: tabular-nums;
    color: var(--o-color-text3);
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

  .info-card-actions {
    flex-direction: column;

    .action-btn {
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

  .versions-table {
    thead th, tbody td {
      padding: 10px 12px;
      font-size: 13px;
    }

    .cell-message {
      max-width: 120px;
    }
  }
}
</style>
