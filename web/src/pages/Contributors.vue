<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Contributor } from '@/api/types'
import { OPagination, OLoading } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'
import flowPrepareSvg from '@/assets/icons/flow-prepare.svg?raw'
import flowClaSvg from '@/assets/icons/flow-cla.svg?raw'
import flowSubmitSvg from '@/assets/icons/flow-submit.svg?raw'
import flowPublishSvg from '@/assets/icons/flow-publish.svg?raw'
const router = useRouter()

const platformNames: Record<string, string> = {
  enterprise: '企业组织',
  community: '社区SIG',
  personal: '个人',
}
const sourceNames: Record<string, string> = {
  github: 'GitHub',
  gitcode: 'GitCode',
}

// 贡献流程四步
const flowSteps = [
  {
    title: '准备Skill',
    desc: '按规范编写 Skill.md',
    icon: flowPrepareSvg,
  },
  {
    title: '签署CLA',
    desc: '首次贡献需签署openEuler CLA',
    icon: flowClaSvg,
    isLink: true,
  },
  {
    title: '提交 Skill',
    desc: '在仓库中提交PR',
    icon: flowSubmitSvg,
  },
  {
    title: 'Skill 发布',
    desc: '审核通过后官网发布',
    icon: flowPublishSvg,
  },
]

// 平台 tabs 顺序：全部 / 企业组织 / 社区SIG / 个人
const tabOrder = ['', 'enterprise', 'community', 'personal'] as const
const currentPlatform = ref<string>('')
const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const contributors = ref<Contributor[]>([])
const total = ref(0)
const platformCounts = ref<Record<string, number>>({})
const loading = ref(true)
const error = ref('')

const page = ref(1)
const pageSize = ref(24)
const pageSizeOptions = [12, 24, 48, 96]

function tabLabel(key: string): string {
  if (!key) return '全部'
  return platformNames[key] || key
}

function tabCount(key: string): number {
  if (!key) return total.value
  return platformCounts.value[key] || 0
}

function displayName(c: Contributor): string {
  return c.name?.trim() || c.author
}

function displayDesc(c: Contributor): string {
  if (c.description?.trim()) return c.description
  if (c.platform === 'personal') return '社区贡献者'
  return ''
}

function avatarSrc(c: Contributor): string | null {
  return c.avatar_url?.trim() || null
}

function buildContributorPath(c: Contributor): string {
  return `/contributors/${encodeURIComponent(c.source)}/${encodeURIComponent(c.author)}`
}

async function fetchContributors() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getContributors({
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value,
      platform: currentPlatform.value || undefined,
      keyword: keyword.value.trim() || undefined,
    })
    contributors.value = res.contributors || []
    total.value = res.total || 0
    platformCounts.value = res.platform_counts || {}
  } catch (e: any) {
    console.error('加载贡献者列表失败:', e)
    error.value = e?.response?.data?.detail || e.message || '加载失败'
    contributors.value = []
    total.value = 0
    platformCounts.value = {}
  } finally {
    loading.value = false
  }
}

function selectPlatform(value: string) {
  if (currentPlatform.value === value) return
  currentPlatform.value = value
  page.value = 1
  oaReport('contributors_filter_platform', {
    module: 'contributors_list',
    platform: value || 'all',
  })
  fetchContributors()
}

function onKeywordInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchContributors()
  }, 300)
}

function onPaginationChange(
  newVal: { page: number; pageSize: number },
  oldVal: { page: number; pageSize: number }
) {
  if (newVal.pageSize !== oldVal.pageSize) {
    page.value = 1
  }
  fetchContributors()
  if (newVal.page !== oldVal.page) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function onClickContributor(c: Contributor) {
  oaReport('contributors_click_card', {
    module: 'contributors_list',
    source: c.source,
    author: c.author,
  })
  router.push(buildContributorPath(c))
}

function onAvatarError(e: Event) {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

onMounted(fetchContributors)
</script>

<template>
  <div class="contributors-page">
    <!-- ========== Hero 区域 ========== -->
    <section class="hero-section">
      <div class="hero-bg">
        <div class="hero-glow hero-glow-left"></div>
        <div class="hero-glow hero-glow-right"></div>
        <div class="hero-code-pattern"></div>
      </div>
      <div class="container-wide relative">
        <h1 class="hero-title">贡献 openEuler Skill</h1>
        <p class="hero-subtitle">每一行经验、每一个自动化脚本、每一个最佳实践，都可以成为帮助社区开发者的Skill。</p>
      </div>
    </section>
    <!-- ========== 贡献流程 ========== -->
    <section class="container-wide flow-section">
      <h2 class="section-title">贡献流程</h2>
      <div class="flow-card">
        <div class="flow-card-bg"></div>
        <div class="flow-steps">
          <template v-for="(step, idx) in flowSteps" :key="step.title">
            <div class="flow-step">
              <div class="flow-icon">
                <span v-html="step.icon"></span>
              </div>
              <div class="flow-step-title">{{ step.title }}</div>
              <div class="flow-step-desc">
                <template v-if="step.isLink">
                  首次贡献需签署
                  <a href="https://clasign.osinfra.cn/sign/Z2l0ZWUlMkZvcGVuZXVsZXI="
                     target="_blank" rel="noopener noreferrer" class="flow-link">openEuler CLA</a>
                </template>
                <template v-else>{{ step.desc }}</template>
              </div>
            </div>
            <div v-if="idx < flowSteps.length - 1" class="flow-connector"></div>
          </template>
        </div>
        <div class="flow-footer">
          <router-link to="/docs/skillhub-publish-and-manage" class="flow-guide-link">
            查看Skill贡献指南
          </router-link>
        </div>
      </div>
    </section>
    <!-- ========== 贡献者广场 ========== -->
    <section class="container-wide plaza-section">
      <h2 class="section-title">贡献者广场</h2>
      <div class="plaza-toolbar">
        <div class="platform-tabs">
          <button
            v-for="key in tabOrder"
            :key="key"
            type="button"
            :class="['tab-btn', { active: currentPlatform === key }]"
            @click="selectPlatform(key)"
          >
            {{ tabLabel(key) }}
            <span class="tab-count">{{ tabCount(key) }}</span>
          </button>
        </div>

        <div class="search-wrap">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="keyword"
            type="text"
            placeholder="搜索贡献者"
            class="search-input"
            @input="onKeywordInput"
          />
        </div>
      </div>
      <!-- 加载态 -->
      <div v-if="loading" class="loading-container">
        <OLoading v-model:visible="loading" size="medium" />
      </div>
      <!-- 错误态 -->
      <div v-else-if="error" class="empty-state">
        <p class="empty-state-text">{{ error }}</p>
      </div>
      <!-- 空态 -->
      <div v-else-if="contributors.length === 0" class="empty-state">
        <div class="empty-illustration">
          <svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="emptyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#e8eef7" stop-opacity="0.6"/>
                <stop offset="100%" stop-color="#e8eef7" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <!-- 底座椭圆 -->
            <ellipse cx="100" cy="140" rx="80" ry="12" fill="url(#emptyGrad)"/>
            <!-- 盒子 -->
            <rect x="55" y="80" width="90" height="50" rx="6" fill="#d8dfe8" opacity="0.7"/>
            <rect x="60" y="70" width="80" height="20" rx="4" fill="#c8d0db" opacity="0.6"/>
            <rect x="85" y="100" width="30" height="6" rx="3" fill="#fff" opacity="0.8"/>
            <!-- 纸飞机 -->
            <g transform="translate(120,50) rotate(20)" opacity="0.5">
              <path d="M0 0 L18 -6 L14 8 Z" fill="#a8b5c4"/>
              <path d="M0 0 L10 4 L14 8" stroke="#a8b5c4" stroke-width="1.5" fill="none"/>
            </g>
            <!-- 飘叶 -->
            <path d="M40 95 Q45 90 50 95 Q45 100 40 95" fill="#b8c5d4" opacity="0.4"/>
            <path d="M155 110 Q160 105 165 110 Q160 115 155 110" fill="#b8c5d4" opacity="0.4"/>
            <path d="M145 90 Q150 88 152 93 Q148 96 145 90" fill="#b8c5d4" opacity="0.3"/>
          </svg>
        </div>
        <p class="empty-state-text">没有匹配的结果</p>
      </div>
      <!-- 贡献者卡片网格 -->
      <div v-else class="contributors-grid">
        <div
          v-for="c in contributors"
          :key="c.id"
          class="contributor-card"
          role="link"
          tabindex="0"
          @click="onClickContributor(c)"
          @keydown.enter.prevent="onClickContributor(c)"
        >
          <div class="card-head">
            <div class="avatar-wrap">
              <img
                v-if="avatarSrc(c)"
                :src="avatarSrc(c)!"
                :alt="displayName(c)"
                class="avatar-img"
                @error="onAvatarError"
              />
              <svg v-else class="avatar-default" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="card-title-col">
              <h3 class="contributor-name">{{ displayName(c) }}</h3>
              <div class="card-tags">
                <span v-if="c.platform" :class="['platform-label', `platform-${c.platform}`]">{{ platformNames[c.platform] || c.platform }}</span>
                <span class="tag tag-source">{{ sourceNames[c.source] || c.source }}</span>
              </div>
            </div>
          </div>
          <p v-if="displayDesc(c)" class="contributor-desc">{{ displayDesc(c) }}</p>
          <div class="card-footer">
            <div class="stat-item">
              <span class="stat-value">{{ c.skill_count }}</span>
              <span class="stat-label">Skills</span>
            </div>
            <div class="stat-item stat-downloads">
              <svg class="download-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 3.29492C12.3544 3.29492 12.6473 3.55827 12.6936 3.89994L12.7 3.99492L12.7 15.5335L17.2249 10.9581C17.4968 10.6833 17.94 10.6808 18.2149 10.9526C18.4623 11.1973 18.489 11.5808 18.2937 11.8554L18.2204 11.9426L12.5008 17.726C12.3635 17.8647 12.1825 17.9341 12.0016 17.9337L12 17.9337C11.6456 17.9337 11.3527 17.6704 11.3064 17.3287L11.3 17.2337L11.3 3.99492C11.3 3.60832 11.6134 3.29492 12 3.29492ZM6.68698 10.8826C6.41393 10.6851 6.03026 10.7087 5.78362 10.9541C5.50957 11.2268 5.50845 11.67 5.78113 11.9441L8.73786 14.9157L8.82444 14.9897C9.09749 15.1872 9.48116 15.1636 9.72781 14.9182C10.0019 14.6455 10.003 14.2023 9.73029 13.9282L6.77356 10.9566L6.68698 10.8826ZM19.0079 19.3594C19.3945 19.3594 19.7079 19.6728 19.7079 20.0594C19.7079 20.4138 19.4445 20.7066 19.1028 20.753L19.0079 20.7594L5.01445 20.7594C4.62785 20.7594 4.31445 20.446 4.31445 20.0594C4.31445 19.705 4.5778 19.4121 4.91947 19.3658L5.01445 19.3594L19.0079 19.3594Z" fill="currentColor" fill-rule="evenodd"/>
              </svg>
              <span class="download-value">{{ c.total_downloads.toLocaleString() }}</span>
              <span class="stat-label">下载量</span>
            </div>
          </div>
        </div>
      </div>
      <!-- 分页 -->
      <div v-if="total > 0 && !loading" class="pagination-row">
        <OPagination
          v-model:page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="pageSizeOptions"
          :layout="['total', 'pagesize', 'pager', 'jumper']"
          @change="onPaginationChange"
        />
      </div>
    </section>
  </div>
</template>

<style lang="scss" scoped>
/* 字体 / 暗色模式公共定义 */
@mixin font-base {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
}
@mixin font-semibold {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
}
@mixin dark {
  .dark &,
  [data-o-theme='e.dark'] & {
    @content;
  }
}
.container-wide {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
/* ===== Hero 区域 ===== */
.hero-section {
  position: relative;
  overflow: hidden;
  padding: 48px 0 32px;
}
.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}
.hero-glow {
  position: absolute;
  width: 480px;
  height: 320px;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
}
.hero-glow-left {
  top: -80px;
  left: -120px;
  background: linear-gradient(135deg, #c7d9f7, #e0d0f7);
  @include dark {
    opacity: 0.08;
    background: #1a2540;
  }
}
.hero-glow-right {
  top: -120px;
  right: -80px;
  background: linear-gradient(135deg, #c7d9f7, #c7e5f7);
  @include dark {
    opacity: 0.08;
    background: #1a2a40;
  }
}
.hero-code-pattern {
  position: absolute;
  top: 0;
  right: 0;
  width: 320px;
  height: 200px;
  background: radial-gradient(ellipse at 80% 20%, rgba(56, 99, 214, 0.06) 0%, transparent 70%);
  &::after {
    content: '';
    position: absolute;
    top: 20px;
    right: 40px;
    width: 160px;
    height: 120px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='120' viewBox='0 0 160 120'%3E%3Cpath d='M120 10 L140 30 L120 50' stroke='%233863d6' stroke-width='2' fill='none' opacity='0.1' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M120 70 L140 90 L120 110' stroke='%233863d6' stroke-width='2' fill='none' opacity='0.1' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") no-repeat;
  }
}
.hero-title {
  @include font-semibold;
  font-size: 40px;
  line-height: 56px;
  color: var(--o-color-info1);
  margin-bottom: 8px;
}
.hero-subtitle {
  @include font-base;
  font-size: var(--o-font_size-text1, 16px);
  line-height: var(--o-line_height-text1, 24px);
  color: var(--o-color-info3);
  margin: 0;
  max-width: 680px;
}
/* ===== 公共标题 ===== */
.section-title {
  @include font-semibold;
  font-size: 28px;
  line-height: 40px;
  color: var(--o-color-info1);
  margin: 0 0 24px;
}
/* ===== 贡献流程 ===== */
.flow-section {
  padding-bottom: 48px;
}
.flow-card {
  position: relative;
  border-radius: 8px;
  background: var(--o-color-fill2);
  padding: 40px 32px 24px;
  overflow: hidden;
  @include dark {
    background: #1a1a1c;
  }
}
.flow-card-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse at 0% 0%, rgba(56, 99, 214, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 100% 100%, rgba(56, 99, 214, 0.06) 0%, transparent 50%);
}
.flow-steps {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
}
.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 0 0 auto;
  width: 160px;
}
.flow-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--o-color-control2-light);
  color: var(--o-color-info1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
  :deep(svg) {
    width: 22px;
    height: 22px;
  }
  @include dark {
    background: #242427;
  }
}
.flow-step-title {
  @include font-semibold;
  font-size: 16px;
  line-height: 24px;
  color: var(--o-color-info1);
  margin-bottom: 4px;
  text-align: center;
}
.flow-step-desc {
  @include font-base;
  font-size: 13px;
  line-height: 20px;
  color: var(--o-color-info3);
  text-align: center;
}
.flow-link {
  color: var(--o-color-link1);
  text-decoration: none;
  @include hover { color: var(--o-color-primary1); }
}
.flow-connector {
  flex: 0 0 auto;
  width: 80px;
  height: 1px;
  background: var(--o-color-control4);
  margin-top: 24px;
  @include dark {
    background: #2a2a2c;
  }
}
.flow-footer {
  position: relative;
  text-align: center;
  margin-top: 24px;
}
.flow-guide-link {
  @include font-base;
  font-size: 14px;
  line-height: 22px;
  color: var(--o-color-link1);
  text-decoration: none;
  @include hover { color: var(--o-color-primary1); }
}
/* ===== 贡献者广场 ===== */
.plaza-section {
  padding-top: 0;
  padding-bottom: 64px;
}
.plaza-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}
.platform-tabs {
  display: flex;
  gap: 0;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--o-color-control4);
  background: var(--o-color-fill2);
  @include dark {
    background: #1a1a1c;
    border-color: #2a2a2c;
  }
}
.tab-btn {
  @include font-base;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  font-size: 14px;
  line-height: 22px;
  color: var(--o-color-info2);
  background: transparent;
  border: none;
  border-right: 1px solid var(--o-color-control4);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  &:last-child {
    border-right: none;
  }
  @include hover {
    color: var(--o-color-info1);
    background: var(--o-color-control2-light);
  }
  &.active {
    background: var(--o-color-primary1);
    color: #fff;
    font-weight: var(--o-font_weight-medium);
    .tab-count {
      color: rgba(255, 255, 255, 0.85);
    }
    @include hover {
      background: var(--o-color-primary1);
      color: #fff;
    }
  }
  @include dark {
    border-right-color: #2a2a2c;
    @include hover {
      background: #242427;
    }
  }
}
.tab-count {
  @include font-base;
  font-size: 13px;
  color: var(--o-color-info3);
}
.search-wrap {
  position: relative;
  width: 260px;
  flex-shrink: 0;
}
.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--o-color-info3);
  pointer-events: none;
}
.search-input {
  width: 100%;
  height: 36px;
  padding: 0 12px 0 36px;
  border: 1px solid var(--o-color-control4);
  border-radius: 4px;
  background: var(--o-color-fill2);
  color: var(--o-color-info1);
  font-family: HarmonyHeiTi;
  font-size: 14px;
  line-height: 22px;
  outline: none;
  transition: border-color 0.15s;
  &::placeholder {
    color: var(--o-color-info3);
  }
  &:focus {
    border-color: var(--o-color-primary1);
  }
  @include dark {
    background: #1a1a1c;
    border-color: #2a2a2c;
  }
}
/* ===== 加载/空态 ===== */
.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0 64px;
  .empty-illustration {
    width: 200px;
    height: 160px;
    margin-bottom: 16px;
  }
  .empty-state-text {
    @include font-base;
    font-size: 14px;
    line-height: 22px;
    color: var(--o-color-info3);
    margin: 0;
  }
}
/* ===== 贡献者卡片网格 ===== */
.contributors-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
}
.contributor-card {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
  outline: none;
  border: none;
  @include hover {
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }
  &:focus-visible {
    box-shadow: 0 0 0 2px var(--o-color-primary1);
  }
  @include dark {
    background: #1a1a1c;
  }
}
.card-head {
  display: flex;
  align-items: center;
  gap: 14px;
}
.avatar-wrap {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--o-color-control3-light);
  display: flex;
  align-items: center;
  justify-content: center;
  @include dark {
    background: #2a2a2c;
  }
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-default {
  width: 26px;
  height: 26px;
  color: var(--o-color-info3);
}
.card-title-col {
  flex: 1;
  min-width: 0;
}
.contributor-name {
  @include font-semibold;
  font-size: 16px;
  line-height: 24px;
  color: var(--o-color-info1);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag {
  @include font-base;
  font-size: 12px;
  line-height: 18px;
  color: var(--o-color-info2);
  border-radius: 4px;
  height: 22px;
  padding: 2px 8px;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  background: var(--o-color-control2-light);
}
.platform-label {
  @include font-base;
  font-size: 12px;
  line-height: 18px;
  padding: 0;
  background: transparent;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.platform-enterprise {
  color: #2e53fa;
  @include dark {
    color: #6b8aff;
  }
}
.platform-community {
  color: #7b25f4;
  @include dark {
    color: #a87aff;
  }
}
.platform-personal {
  color: #e2127a;
  @include dark {
    color: #ff6bb0;
  }
}
.tag-source {
  background: var(--o-color-white);
  border: 1px solid var(--o-color-control4);
  color: var(--o-color-info3);
  @include dark {
    background: #242427;
    border-color: #2a2a2c;
  }
}
.contributor-desc {
  @include font-base;
  font-size: 13px;
  line-height: 20px;
  color: var(--o-color-info3);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--o-color-control3-light);
  margin-top: auto;
  @include dark {
    border-top-color: #2a2a2c;
  }
}
.stat-item, .stat-downloads {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.download-icon {
  width: 12px;
  height: 12px;
  color: hsla(0, 0%, 0%, 0.6);
  flex-shrink: 0;
  transform: translateY(1px);
  @include dark {
    color: hsla(0, 0%, 100%, 0.6);
  }
}
.download-value, .stat-value, .stat-label {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 12px;
  line-height: 18px;
  color: hsla(0, 0%, 0%, 0.6);
}
.dark .download-value,
.dark .stat-value,
.dark .stat-label,
[data-o-theme='e.dark'] .download-value,
[data-o-theme='e.dark'] .stat-value,
[data-o-theme='e.dark'] .stat-label {
  color: hsla(0, 0%, 100%, 0.6);
}
/* ===== 分页 ===== */
.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 32px;
}
/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .contributors-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .flow-steps {
    flex-wrap: wrap;
    gap: 16px;
  }
  .flow-connector {
    display: none;
  }
}
@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
    line-height: 40px;
  }
  .section-title {
    font-size: 22px;
    line-height: 32px;
  }
  .flow-card {
    padding: 24px 16px 20px;
  }
  .flow-step {
    width: 140px;
  }
  .plaza-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .platform-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
  }
  .tab-btn {
    flex-shrink: 0;
    padding: 8px 14px;
  }
  .search-wrap {
    width: 100%;
  }
  .contributors-grid {
    grid-template-columns: 1fr;
  }
}
</style>
