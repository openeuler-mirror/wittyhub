<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Contributor } from '@/api/types'
import { OPagination, OLoading, OInput, OTab, OTabPane } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'
import flowBgLight from '@/assets/bg/card-bg.png'
import flowBgDark from '@/assets/bg/card-bg-dark.png'
import flowPrepareSvg from '@/assets/icons/flow-prepare.svg?raw'
import flowClaSvg from '@/assets/icons/flow-cla.svg?raw'
import flowSubmitSvg from '@/assets/icons/flow-submit.svg?raw'
import flowPublishSvg from '@/assets/icons/flow-publish.svg?raw'
const router = useRouter()
const appStore = useAppStore()

const platformNames: Record<string, string> = {
  enterprise: '企业组织',
  community: '社区SIG',
  personal: '个人',
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
const activeTab = ref('all')
const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const contributors = ref<Contributor[]>([])
const total = ref(0)
/* grand_total：仅 keyword 筛选下的全平台总数，用于"全部" tab 计数，
   切换 platform 时不变化 */
const grandTotal = ref(0)
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
  /* "全部" tab 始终显示全平台总数（仅 keyword 筛选），切换 platform 时不变化 */
  if (!key) return grandTotal.value
  return platformCounts.value[key] || 0
}

function displayName(c: Contributor): string {
  return c.name?.trim() || c.author
}

/* 社区 SIG 贡献者名称多为 sig-xxx，头像统一显示 S 不直观；
   以 sig- 开头时，取 sig- 后首个单词的首字母大写作为头像字母 */
function avatarLetter(c: Contributor): string {
  const name = displayName(c)
  const m = name.match(/^sig-+\s*([A-Za-z])/)
  if (m) return m[1]!.toUpperCase()
  return name.charAt(0).toUpperCase()
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
    grandTotal.value = res.grand_total ?? res.total ?? 0
    platformCounts.value = res.platform_counts || {}
  } catch (e: any) {
    console.error('加载贡献者列表失败:', e)
    error.value = e?.response?.data?.detail || e.message || '加载失败'
    contributors.value = []
    total.value = 0
    grandTotal.value = 0
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

function onTabChange(value: string | number) {
  selectPlatform(String(value) === 'all' ? '' : String(value))
}

/* 下载量按中文习惯格式化（4.5万） */
function formatDownloads(n: number): string {
  if (n >= 10000) {
    const w = n / 10000
    return `${w >= 100 ? Math.round(w) : Math.round(w * 10) / 10}万`
  }
  return String(n)
}

watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchContributors()
  }, 300)
})

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
      <div class="absolute inset-0 pointer-events-none">
        <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" class="w-full h-full object-cover" />
      </div>
      <div class="container-wide relative h-full flex flex-col justify-center">
        <h1 class="hero-title">贡献 openEuler Skill</h1>
        <p class="hero-subtitle">每一行经验、每一个自动化脚本、每一个最佳实践，都可以成为帮助社区开发者的Skill。</p>
      </div>
    </section>
    <!-- ========== 贡献流程 ========== -->
    <section class="container-wide flow-section">
      <h2 class="section-title">贡献流程</h2>
      <div class="flow-card">
        <img :src="appStore.isDark ? flowBgDark : flowBgLight" alt="" class="flow-card-bg" />
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
        <!-- 按钮页签 466×48，容器 #EDEFF2，选中白底蓝字半粗体 -->
        <OTab v-model="activeTab" variant="button" size="large" class="platform-tabs" @change="onTabChange">
          <OTabPane v-for="key in tabOrder" :key="key" :value="key || 'all'">
            <template #nav>
              {{ tabLabel(key) }}<span class="tab-count">{{ tabCount(key) }}</span>
            </template>
          </OTabPane>
        </OTab>

        <!-- 搜索框 320×48，白底 1px 边框，圆角 4px -->
        <div class="search-wrap">
          <OInput v-model="keyword" placeholder="搜索贡献者" size="large" round="4px" class="search-input">
            <template #prefix>
              <svg class="search-icon" width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.549 16.523l0.087 0.074 2.76 2.754c0.274 0.273 0.274 0.716 0.001 0.99-0.246 0.246-0.629 0.271-0.903 0.075l-0.087-0.074-2.76-2.754c-0.274-0.273-0.274-0.716-0.001-0.99 0.246-0.246 0.629-0.271 0.903-0.075zM10.821 3.454c4.099 0 7.423 3.323 7.423 7.423s-3.323 7.423-7.423 7.423c-4.099 0-7.423-3.323-7.423-7.423s3.323-7.423 7.423-7.423zM10.821 4.854c-3.326 0-6.023 2.696-6.023 6.023s2.696 6.023 6.023 6.023c3.326 0 6.023-2.696 6.023-6.023s-2.696-6.023-6.023-6.023z" fill="currentColor"></path>
              </svg>
            </template>
          </OInput>
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
            <div :class="['avatar-wrap', c.platform ? `avatar-${c.platform}` : 'avatar-default']">
              <img
                v-if="avatarSrc(c)"
                :src="avatarSrc(c)!"
                :alt="displayName(c)"
                class="avatar-img"
                @error="onAvatarError"
              />
              <span v-else class="avatar-fallback">{{ avatarLetter(c) }}</span>
            </div>
            <h3 class="contributor-name">{{ displayName(c) }}</h3>
            <span v-if="c.platform" class="platform-label">{{ platformNames[c.platform] || c.platform }}</span>
          </div>
          <p class="contributor-desc">{{ displayDesc(c) }}</p>
          <div class="card-footer">
            <span class="stat-text">{{ c.skill_count }} skills</span>
            <span class="stat-text">{{ formatDownloads(c.total_downloads) }} 下载量</span>
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
/* 与 AppHeader 的 ContentWrapper 同宽（1488px + 24px padding），
   保证 hero 标题/区块标题与 header logo 左缘对齐 */
.container-wide {
  max-width: 1488px;
  margin: 0 auto;
  padding: 0 24px;
}
/* ===== Hero 区域 ===== */
/* 高度与主页 hero 保持一致：背景图为 object-cover，容器宽高比相同时
   纹理的缩放与裁切位置才能与主页完全对齐 */
.hero-section {
  position: relative;
  overflow: hidden;
  height: 319.2px;
}
.hero-title {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: 48px;
  line-height: 64px;
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info1);
  margin-bottom: 8px;
}
.hero-subtitle {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 18px;
  line-height: 26px;
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info3);
  margin: 0;
}
/* ===== 公共标题 ===== */
.section-title {
  @include font-semibold;
  font-size: 40px;
  line-height: 56px;
  color: var(--o-color-info1);
  margin: 0 0 24px;
}
/* ===== 贡献流程 ===== */
.flow-section {
  padding-bottom: 48px;
}
.flow-card {
  position: relative;
  /* 设计稿卡片背景图（卡片背景.png / 卡片背景-dark.png，2976×400 @2x），
     圆角 4px，图片绝对铺满；底色仅作加载前回退 */
  border-radius: 4px;
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
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
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
  /* 允许文字单行溢出（设计稿图标行 56+52*2=160，文字行各自宽度） */
  overflow: visible;
}
.flow-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--o-color-control2-light);
  color: var(--o-color-info1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
  :deep(svg) {
    width: 24px;
    height: 24px;
  }
  @include dark {
    background: #242427;
  }
}
.flow-step-title {
  @include font-semibold;
  font-size: 18px;
  line-height: 26px;
  color: var(--o-color-info1);
  margin-bottom: 4px;
  text-align: center;
  white-space: nowrap;
  overflow: visible;
}
.flow-step-desc {
  @include font-base;
  font-size: 16px;
  line-height: 24px;
  /* 设计稿 opacity=0.6 (#00000099) */
  color: var(--o-color-info3);
  text-align: center;
  white-space: nowrap;
  overflow: visible;
}
.flow-link {
  color: var(--o-color-link1);
  text-decoration: none;
  @include hover { color: var(--o-color-primary1); }
}
.flow-connector {
  flex: 0 0 auto;
  width: 160px;
  border-top: 1px solid hsl(0, 0%, 0%);
  margin-top: 28px;
  @include dark {
    border-top-color: hsl(0, 0%, 100%);
  }
}
.flow-footer {
  position: relative;
  text-align: center;
  margin-top: 24px;
}
.flow-guide-link {
  @include font-base;
  font-size: 16px;
  line-height: 24px;
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
/* 平台 tabs：设计稿按钮页签——容器 466×48 圆角 4px 背景 #EDEFF2(fill3)，
   选中 tab 白底(fill2) 蓝字(primary1) 半粗体 18px，tab 高 40 间距 4，计数紧跟文字 */
.platform-tabs {
  flex-shrink: 0;
  /* tab 总高 = 26(行高) + 6*2(padding) + 2(border) = 40，容器 40 + 4*2 = 48 */
  --tab-nav-text-size: 18px;
  --tab-nav-text-height: 26px;
  --tab-btn-radius: 4px;
  /* 未选中文字 #000000(info1)（组件默认 info2） */
  --tab-icon-color: var(--o-color-info1);
  font-family: HarmonyHeiTi;
  .tab-count {
    margin-left: 4px;
    font-weight: var(--o-font_weight-regular);
    color: var(--o-color-info3);
  }
  :deep(.o-tab-nav-active) {
    .tab-count {
      font-weight: var(--o-font_weight-semibold);
      color: var(--o-color-primary1);
    }
  }
}
/* 搜索框：设计稿 320×48，白底，1px 边框 #000 op=0.25(control1)，圆角 4px */
.search-wrap {
  width: 320px;
  flex-shrink: 0;
}
.search-input {
  width: 100%;
  --_box-height: 48px;
  font-family: HarmonyHeiTi;
}
.search-icon {
  width: 24px;
  height: 24px;
  color: var(--o-color-info2);
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
/* 贡献者卡片：设计稿 474×192 白底圆角 8px，padding 24 */
.contributor-card {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 24px;
  display: flex;
  flex-direction: column;
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
/* 头部行：头像 30×30 + 8px 间距 + 名称，标签右对齐（设计稿容器 162 高 30） */
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 30px;
}
/* 头像：30×30 圆形，背景平台色，首字母 22px 半粗体白色 */
.avatar-wrap {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-enterprise {
  background: #2e53fa;
  @include dark { background: #6b8aff; }
}
.avatar-community {
  background: #7b25f4;
  @include dark { background: #a87aff; }
}
.avatar-personal {
  background: #e2127a;
  @include dark { background: #ff6bb0; }
}
.avatar-default {
  background: var(--o-color-primary1);
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-fallback {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: 22px;
  line-height: 30px;
  color: #FFFFFF;
  text-align: center;
}
.contributor-name {
  @include font-semibold;
  font-size: 22px;
  line-height: 30px;
  color: var(--o-color-info1);
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 平台标签：右上角，高 24，白底 1px 边框 op=0.25(control1)，圆角 4px，12px 黑字 */
.platform-label {
  margin-left: auto;
  flex-shrink: 0;
  @include font-base;
  font-size: 12px;
  line-height: 18px;
  color: var(--o-color-info1);
  height: 24px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--o-color-control1);
  border-radius: 4px;
  background: transparent;
}
.contributor-desc {
  @include font-base;
  font-size: 16px;
  line-height: 24px;
  color: var(--o-color-info3);
  margin: 12px 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 48px;
}
/* 底部：分隔线（距描述 24px）+ 统计（距线 12px），12px op=0.60(info3) */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 12px;
  border-top: 1px solid var(--o-color-control3-light);
  @include dark {
    border-top-color: #2a2a2c;
  }
}
.stat-text {
  @include font-base;
  font-size: 12px;
  line-height: 18px;
  color: var(--o-color-info3);
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
  .search-wrap {
    width: 100%;
  }
  .contributors-grid {
    grid-template-columns: 1fr;
  }
}
</style>
