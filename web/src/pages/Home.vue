<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSkillStore } from '@/stores/skill'
import { useAppStore } from '@/stores/app'
import { OInput, OTab, OTabPane, OPagination, ODropdown, ODropdownItem, OLoading, OLink } from '@opensig/opendesign'
import FilterSidebar from '@/components/FilterSidebar.vue'
import SkillCard from '@/components/SkillCard.vue'
import SkillListItem from '@/components/SkillListItem.vue'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'
import viewGridSvg from '@/assets/icons/view-grid.svg?raw'
import viewListSvg from '@/assets/icons/view-list.svg?raw'
import cardBgLight from '@/assets/bg/card-bg-light.png'
import cardBgDark from '@/assets/bg/card-bg-dark.png'
import submitSkillSvg from '@/assets/icons/submit-skill.svg?raw'
import submitLinkSvg from '@/assets/icons/submit-link.svg?raw'
import emptyStateSvg from '@/assets/icons/empty-state.svg?raw'

const skillStore = useSkillStore()
const appStore = useAppStore()
const route = useRoute()
const router = useRouter()
const searchInput = ref('')

const sortOptions = [
  { label: '全部时间', value: 'all' },
  { label: '近7天', value: 'week' },
  { label: '近30天', value: 'month' }
]

const pageSizeOptions = [12, 24, 48, 96]

const currentSortLabel = computed(() => {
  const opt = sortOptions.find(o => o.value === skillStore.filter.sortPeriod)
  return opt ? opt.label : '全部时间'
})

const isSearchPage = computed(() => route.path === '/skills/search')
const searchQuery = computed(() => route.query.q as string || '')

onMounted(async () => {
  if (searchQuery.value) {
    searchInput.value = searchQuery.value
    skillStore.setFilter('keyword', searchQuery.value)
  }

  if (route.params.category) {
    skillStore.setFilter('category', route.params.category as string)
  }

  await Promise.all([
    skillStore.fetchStats(),
    skillStore.fetchCategories(),
    skillStore.fetchSkills()
  ])
})

watch(() => route.query.q, (newQ) => {
  if (newQ !== undefined) {
    searchInput.value = newQ as string
    skillStore.setFilter('keyword', newQ as string)
    skillStore.fetchSkills()
  }
})

function handleSearch() {
  const q = searchInput.value.trim()
  if (q) {
    router.push({
      path: '/skills/search',
      query: { q }
    })
  } else {
    router.push('/')
    skillStore.setFilter('keyword', '')
    skillStore.fetchSkills()
  }
}

function handleClear() {
  searchInput.value = ''
  router.push('/')
  skillStore.setFilter('keyword', '')
  skillStore.fetchSkills()
}

function setSortBy(sort: 'hot' | 'latest' | 'downloads') {
  skillStore.setFilter('sortBy', sort)
  skillStore.fetchSkills()
}

function setSortPeriod(period: string) {
  skillStore.setFilter('sortPeriod', period)
  skillStore.fetchSkills()
}

function setViewMode(mode: 'card' | 'list') {
  skillStore.setFilter('viewMode', mode)
}

function onPaginationChange(
  newVal: { page: number; pageSize: number },
  oldVal: { page: number; pageSize: number }
) {
  if (newVal.pageSize !== oldVal.pageSize) {
    skillStore.filter.page = 1
  }
  skillStore.fetchSkills()
  if (newVal.page !== oldVal.page) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}
</script>

<template>
  <div>
    <!-- Hero 区域 -->
    <section class="hero-section relative overflow-hidden" style="height: 319.2px">
      <!-- 设计稿背景图 -->
      <div class="absolute inset-0 pointer-events-none">
        <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" class="w-full h-full object-cover" />
      </div>

      <div class="container-wide relative h-full flex flex-col items-center justify-center text-center">
        <h1 class="hero-title">SkillHub</h1>
        <p class="hero-subtitle">探索、评估、贡献openEuler技能</p>
        <p class="hero-stats">
          <span class="hero-stats-number">{{ skillStore.stats?.total_skills?.toLocaleString() || '200' }}</span>
          Skills
          <span class="mx-2 text-[var(--o-color-text3)]">|</span>
          <span class="hero-stats-number">{{ skillStore.stats?.total_categories || '15' }}</span>
          领域分类
        </p>

        <!-- 搜索框 -->
        <div style="max-width:620px; width:100%; margin:0 auto">
          <OInput
            v-model="searchInput"
            placeholder="搜索 Skill"
            size="large"
            round="8px"
            clearable
            @press-enter="handleSearch"
            @clear="handleClear"
            style="width: 100%"
          >
            <template #prefix>
              <svg class="search-icon" width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.549 16.523l0.087 0.074 2.76 2.754c0.274 0.273 0.274 0.716 0.001 0.99-0.246 0.246-0.629 0.271-0.903 0.075l-0.087-0.074-2.76-2.754c-0.274-0.273-0.274-0.716-0.001-0.99 0.246-0.246 0.629-0.271 0.903-0.075zM10.821 3.454c4.099 0 7.423 3.323 7.423 7.423s-3.323 7.423-7.423 7.423c-4.099 0-7.423-3.323-7.423-7.423s3.323-7.423 7.423-7.423zM10.821 4.854c-3.326 0-6.023 2.696-6.023 6.023s2.696 6.023 6.023 6.023c3.326 0 6.023-2.696 6.023-6.023s-2.696-6.023-6.023-6.023z" fill="currentColor"></path>
              </svg>
            </template>
          </OInput>
        </div>
      </div>
    </section>

    <!-- 主要内容区 -->
    <section class="container-wide py-6">
      <div class="flex gap-8">
        <!-- 左侧筛选侧栏 -->
        <div class="w-60 flex-shrink-0 sticky bottom-0 self-start">
          <FilterSidebar />
        </div>

        <!-- 右侧内容区 -->
        <div class="flex-1 min-w-0">
          <!-- 搜索结果提示 + 工具栏 -->
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <OTab
                v-model="skillStore.filter.sortBy"
                variant="button"
                round="4px"
                size="large"
                header-class="sort-tab"
                @change="skillStore.fetchSkills()"
              >
                <OTabPane value="hot" label="热门" />
                <OTabPane value="latest" label="最新" />
              </OTab>

              <div class="sort-dropdown-wrapper" v-if="skillStore.filter.sortBy !== 'latest'">
              <ODropdown
                trigger="click"
                option-width-mode="min-width"
                option-wrap-class="sort-period-dropdown"
                style="--dropdown-item-bg-color-hover: var(--o-color-control2-light)"
              >
                <button class="sort-period-btn">
                  {{ currentSortLabel }}
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M5.759 8.873a.7.7 0 0 1 .918-.063l.072.063 5.016 5.016a.3.3 0 0 0 .37.043l.054-.043 5.062-5.062a.7.7 0 0 1 1.053.918l-.063.072-5.062 5.062a1.7 1.7 0 0 1-2.296.099l-.108-.099-5.016-5.016a.7.7 0 0 1 0-.99"/>
                  </svg>
                </button>
                <template #dropdown>
                  <ODropdownItem
                    v-for="opt in sortOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                    @click="setSortPeriod(opt.value)"
                  />
                </template>
              </ODropdown>
              </div>

              <!-- 搜索结果提示：数据加载完成后再显示 -->
              <div v-if="isSearchPage && searchQuery && !skillStore.loading" class="text-sm text-[var(--o-color-text3)]">
                为您找到 <span class="text-[var(--o-color-info1)] font-semibold">{{ skillStore.total }}</span> 个与 "{{ searchQuery }}" 匹配的搜索结果
              </div>
            </div>

            <OTab
                v-model="skillStore.filter.viewMode"
                variant="button"
                round="4px"
                size="large"
                header-class="view-tab"
              >
                <OTabPane value="card">
                  <template #nav>
                    <span class="w-5 h-5 flex items-center justify-center" v-html="viewGridSvg" title="卡片视图"></span>
                  </template>
                </OTabPane>
                <OTabPane value="list">
                  <template #nav>
                    <span class="w-5 h-5 flex items-center justify-center" v-html="viewListSvg" title="列表视图"></span>
                  </template>
                </OTabPane>
              </OTab>
          </div>

          <!-- 加载态 -->
          <div v-if="skillStore.loading" class="loading-container">
            <OLoading v-model:visible="skillStore.loading" size="medium" />
          </div>

          <!-- 空态 -->
          <div v-else-if="!skillStore.loading && skillStore.skills.length === 0" class="text-center py-16">
            <div class="empty-state-svg w-64 mx-auto mb-6" v-html="emptyStateSvg"></div>
            <p class="text-[var(--o-color-text3)]">暂无相关 Skill</p>
          </div>

          <!-- Skill 列表 -->
          <template v-else-if="!skillStore.loading">
            <div v-if="skillStore.filter.viewMode === 'card'" class="grid grid-cols-3 gap-4">
              <SkillCard v-for="skill in skillStore.skills" :key="skill.id" :skill="skill" />
            </div>
            <div v-else class="border border-gray-200 rounded-lg dark:border-gray-700 overflow-hidden">
              <!-- 列表视图表头 -->
              <div class="flex items-center gap-8 px-6 py-4 bg-white dark:bg-gray-800 list-header" style="font-family: HarmonyHeiTi; font-size: 14px; line-height: 22px; font-weight: 600; letter-spacing: 0px; border-bottom: 1px solid #002FA7;">
                <div class="flex-1 min-w-0 max-w-[560px]">名称</div>
                <div class="w-[100px]">分类</div>
                <div class="w-[100px]">风险等级</div>
                <div class="w-[100px]">下载量</div>
                <div class="w-36">贡献者</div>
              </div>
              <SkillListItem v-for="skill in skillStore.skills" :key="skill.id" :skill="skill" />
            </div>
          </template>

          <!-- 分页 -->
          <div v-if="skillStore.total > 0 && !skillStore.loading" class="flex items-center justify-between mt-8">
              <div></div>
              <OPagination
                v-model:page="skillStore.filter.page"
                v-model:page-size="skillStore.filter.pageSize"
                :total="skillStore.total"
                :page-sizes="pageSizeOptions"
                :layout="['total', 'pagesize', 'pager', 'jumper']"
                @change="onPaginationChange"
              />
            </div>
        </div>
      </div>

      <!-- 提交新Skill区 -->
      <div class="mt-16 text-center">
        <h2 class="submit-title">提交新Skill</h2>
        <p class="text-[var(--o-color-info3)] text-base leading-6">参与社区贡献，与开发者共建SkillHub</p>
      </div>

      <div class="mt-8 overflow-hidden relative submit-wrapper" style="border-radius: var(--o-radius-s);">
        <img :src="appStore.isDark ? cardBgDark : cardBgLight" alt="" class="absolute inset-0 w-full h-full object-cover pointer-events-none" />
        <div class="relative p-8 submit-card">
          <h3 class="text-lg font-semibold text-[var(--o-color-info1)] mb-4">在仓库中提交PR</h3>
          <p class="submit-desc">
            Fork <OLink href="https://gitcode.com/openeuler/wittyhub" target="_blank" rel="noopener noreferrer" color="normal" size="auto">openeuler/wittyhub</OLink> 仓库并Clone到本地，提交单个Skill 或 Skill 仓库链接，待PR审核通过后入仓，同步至首屏展示。
          </p>

          <div class="grid grid-cols-2 gap-8 submit-methods-grid">
            <div>
              <h3 class="method-title">方式1</h3>
              <p class="method-sub-label">
                <span v-html="submitSkillSvg"></span>
                提交单个Skill
              </p>
              <p class="method-desc">
                在skills目录下创建user/skillname目录，包含Skill.md 文件和其他依赖文件。
              </p>
            </div>

            <div>
              <h3 class="method-title">方式2</h3>
              <p class="method-sub-label">
                <span v-html="submitLinkSvg"></span>
                提交Skill仓库链接，自动拉取Skill
              </p>
              <p class="method-desc">在skills/skill-repo.yaml里填写你的repo。</p>
              <div class="code-sample">
                <div>personal_repo:</div>
                <div>&nbsp;&nbsp;- url: https://gitcode.com/user/reponame</div>
                <div>&nbsp;&nbsp;&nbsp;&nbsp;branch: main  --选填</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.container-wide {
  max-width: 1488px;
  margin: 0 auto;
  padding: 0 24px;
}

/* 加载容器 */
.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* 搜索图标 */
.search-icon {
  width: 24px;
  height: 24px;
  color: var(--o-color-text3);
}

/* Hero 标题 */
.hero-title {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: 40px;
  line-height: 56px;
  color: var(--o-color-info1);
  text-align: center;
  margin-bottom: 12px;
}

.hero-subtitle {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: var(--o-r-font_size-text2);
  line-height: var(--o-r-line_height-text2);
  color: var(--o-color-info1);
  text-align: center;
  margin-bottom: 8px;
}

.hero-stats {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: var(--o-r-font_size-text1);
  line-height: var(--o-r-line_height-text1);
  color: var(--o-color-info3);
  text-align: center;
  margin-bottom: 32px;
}

.hero-stats-number {
  font-weight: var(--o-font_weight-medium);
  color: var(--o-color-text3);
}

/* 列表视图表头 */
.list-header {
  color: #000000CC;
}

[data-o-theme="e.dark"] .list-header,
.dark .list-header {
  color: #C9CDD4;
}

/* 提交新Skill 标题 */
.submit-title {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: 40px;
  line-height: 56px;
  letter-spacing: -0.32px;
  text-align: center;
  color: var(--o-color-info1);
  margin-bottom: 12px;
}

[data-o-theme="e.dark"] .submit-title,
.dark .submit-title {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 32px;
  line-height: normal;
  letter-spacing: -0.32px;
  text-align: center;
}

[data-o-theme="e.dark"] .submit-title + p,
.dark .submit-title + p {
  color: var(--o-color-info1);
}

/* 提交新Skill 描述文本 */
.submit-desc {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text1);
  line-height: var(--o-line_height-text1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info3);
  margin-bottom: 24px;
}

/* 提交方式标题 */
.method-title {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: var(--o-font_size-h3);
  line-height: var(--o-line_height-h3);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info1);
  margin-bottom: 8px;
}

/* 提交方式子标签 */
.method-sub-label {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text1);
  line-height: var(--o-line_height-text1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info1);
  margin-bottom: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.method-sub-label svg {
  background: #FFFFFF;
  border-radius: 4px;
}

/* 提交方式描述 */
.method-desc {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text1);
  line-height: var(--o-line_height-text1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info3);
  margin-bottom: 12px;
}

/* 代码示例块 */
.code-sample {
  background: var(--o-color-control2-light);
  border-radius: 4px;
  padding: 12px;
  font-family: HarmonyHeiTi;
  font-weight: 400;
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info3);
}

[data-o-theme="e.dark"] .code-sample,
.dark .code-sample {
  background: var(--o-color-control2-light);
}

/* 提交卡片 */
.submit-wrapper {
  background: #FFFFFF;
}

[data-o-theme="e.dark"] .submit-wrapper,
.dark .submit-wrapper {
  background: #242427;
}

.submit-card {
  position: relative;
  z-index: 1;
  border-radius: var(--o-radius-s);
}

/* 方式1和方式2之间的竖分割线 */
.submit-methods-grid {
  position: relative;
}

.submit-methods-grid::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  background: var(--o-color-control4);
  transform: translateX(-50%);
  pointer-events: none;
}

/* OTab button variant: 排序切换 (热门/最新) */
.sort-tab {
  width: 148px;

  :deep(.o-tab-head) {
    background: var(--o-color-fill1);
    border-radius: 4px;
    padding: 4px;
    height: 48px !important;
    border: none;
    box-sizing: border-box;
  }

  :deep(.o-tab-navs) {
    gap: 0;
  }

  :deep(.o-tab-nav) {
    width: 68px !important;
    min-width: 68px !important;
    height: 40px;
    padding: 0;
    border: none !important;
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    font-size: var(--o-r-font_size-text2);
    line-height: var(--o-r-line_height-text2);
    color: var(--o-color-primary1) !important;
    border-radius: 4px !important;
    background: transparent !important;
    justify-content: center;
    align-items: center;

    &:hover:not(.is-active) {
      background: color-mix(in srgb, var(--o-color-primary1) 8%, transparent);
    }

    &.is-active {
      font-weight: var(--o-font_weight-semibold);
      background: var(--o-color-fill2) !important;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    }
  }
}

/* OTab button variant: 视图切换 (卡片/列表) */
.view-tab {
  --tab-nav-padding: 8px 16px;

  :deep(.o-tab-head) {
    background: var(--o-color-fill1);
    border-radius: 4px;
    padding: 3px;
    min-height: auto;
    border: none;
    box-sizing: border-box;
  }

  :deep(.o-tab-navs) {
    gap: 0;
  }

  :deep(.o-tab-nav) {
    width: 44px !important;
    min-width: 44px !important;
    padding: 0;
    border: none !important;
    color: var(--o-color-primary1) !important;
    border-radius: 4px !important;
    background: transparent !important;
    justify-content: center;
    align-items: center;

    &:hover:not(.is-active) {
      background: color-mix(in srgb, var(--o-color-primary1) 8%, transparent);
    }

    &.is-active {
      background: var(--o-color-fill2) !important;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    }
  }
}

/* 空态 SVG */
.empty-state-svg {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 8 / 7;
}

.empty-state-svg svg {
  width: 100%;
  height: 100%;
}

/* OSelect 覆盖：与筛选栏统一 */
:deep(.o-select) {
  --select-height: 32px;
  --select-radius: 4px;
  --select-text-size: 16px;
  width: 120px;
  border: none !important;
  background: transparent !important;
}

:deep(.o-select-input) {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-r-font_size-text1);
  line-height: var(--o-r-line_height-text1);
  color: var(--o-color-info1);
  text-align: center;
}

:deep(.o-option-item) {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-r-font_size-text1);
  line-height: var(--o-r-line_height-text1);
  color: var(--o-color-info1);
  text-align: right;
}

/* 分页下拉框 */
.page-size-select {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-tip1);
  line-height: var(--o-line_height-tip1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info1);
}

[data-o-theme="e.dark"] .page-size-select,
.dark .page-size-select {
  background-color: #242427;
}

/* 分页信息文本 */
.pagination-info {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-tip1);
  line-height: var(--o-line_height-tip1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info2);
}

/* OPagination 统一高度 32px */
:deep(.o-pagination-wrap) {
  --pagination-item-size: 32px;
  --pagination-arrow-size: 32px;
}

:deep(.o-pagination-select.o-select) {
  height: 32px !important;
  border-radius: 4px !important;
  background: var(--o-color-white) !important;
  border: 1px solid #0000003F !important;
  transition: border-color var(--o-duration-s) var(--o-easing-standard);

  &:hover {
    border-color: #002FA7 !important;
  }
}

:deep(.o-pagination-input.o-input-number) {
  height: 32px !important;
  --input-height: 32px;
}

:deep(.o-pagination-input.o-input-number .o_input-input) {
  height: 32px !important;
}

.sort-dropdown-wrapper {
  margin-left: 14px;
}

.sort-period-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 32px;
  width: 92px;
  min-width: 92px;
  max-width: 92px;
  box-sizing: border-box;
  padding: 0 4px;
  border: none;
  background: none;
  color: #000000;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  text-align: right;
  cursor: pointer;
  border-radius: var(--o-radius-s);
  white-space: nowrap;
  width: auto;

  &:hover {
    color: #002FA7;
  }
}

[data-o-theme="e.dark"] .sort-period-btn:hover,
.dark .sort-period-btn:hover {
  color: var(--o-color-primary1);
}

[data-o-theme="e.dark"] .sort-period-btn,
.dark .sort-period-btn {
  color: var(--o-color-info1);
}

/* 分页跳转输入框 */
:deep(.o_box-main) {
  border-radius: 4px;
  background: var(--o-color-white);
  border: 1px solid #00000019;
}

/* 分页箭头图标替换 */
:deep(.o-icon-chevron-left),
:deep(.o-icon-chevron-right) {
  width: 24px;
  height: 24px;
}

:deep(.o-icon-chevron-left path),
:deep(.o-icon-chevron-right path) {
  display: none;
}

:deep(.o-icon-chevron-left) {
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath d='M14.754 5.764c0.251 0.251 0.271 0.644 0.063 0.918l-0.063 0.072-5.016 5.016c-0.1 0.1-0.115 0.254-0.043 0.37l0.043 0.054 5.062 5.062c0.273 0.273 0.273 0.717 0 0.99-0.251 0.251-0.644 0.271-0.918 0.063l-0.072-0.063-5.062-5.062c-0.629-0.629-0.662-1.628-0.099-2.296l0.099-0.108 5.016-5.016c0.273-0.273 0.717-0.273 0.99 0z'/%3E%3C/svg%3E") no-repeat center;
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath d='M14.754 5.764c0.251 0.251 0.271 0.644 0.063 0.918l-0.063 0.072-5.016 5.016c-0.1 0.1-0.115 0.254-0.043 0.37l0.043 0.054 5.062 5.062c0.273 0.273 0.273 0.717 0 0.99-0.251 0.251-0.644 0.271-0.918 0.063l-0.072-0.063-5.062-5.062c-0.629-0.629-0.662-1.628-0.099-2.296l0.099-0.108 5.016-5.016c0.273-0.273 0.717-0.273 0.99 0z'/%3E%3C/svg%3E") no-repeat center;
  mask-size: contain;
  -webkit-mask-size: contain;
  background: currentColor;
}

:deep(.o-icon-chevron-right) {
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath d='M9.246 5.764c-0.251 0.251-0.271 0.644-0.063 0.918l0.063 0.072 5.016 5.016c0.1 0.1 0.115 0.254 0.043 0.37l-0.043 0.054-5.062 5.062c-0.273 0.273-0.273 0.717 0 0.99 0.251 0.251 0.644 0.271 0.918 0.063l0.072-0.063 5.062-5.062c0.629-0.629 0.662-1.628 0.099-2.296l-0.099-0.108-5.016-5.016c-0.273-0.273-0.717-0.273-0.99 0z'/%3E%3C/svg%3E") no-repeat center;
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath d='M9.246 5.764c-0.251 0.251-0.271 0.644-0.063 0.918l0.063 0.072 5.016 5.016c0.1 0.1 0.115 0.254 0.043 0.37l-0.043 0.054-5.062 5.062c-0.273 0.273-0.273 0.717 0 0.99 0.251 0.251 0.644 0.271 0.918 0.063l0.072-0.063 5.062-5.062c0.629-0.629 0.662-1.628 0.099-2.296l-0.099-0.108-5.016-5.016c-0.273-0.273-0.717-0.273-0.99 0z'/%3E%3C/svg%3E") no-repeat center;
  mask-size: contain;
  -webkit-mask-size: contain;
  background: currentColor;
}
</style>

<style lang="scss">
/* Teleport 到 body 的下拉面板全局样式 */
.sort-period-dropdown {
  width: 116px !important;
  min-width: 116px;
  transform: translateX(-12px);
}

[data-o-theme="e.dark"] .o-pagination-select.o-select,
.dark .o-pagination-select.o-select {
  background: #242427 !important;
  border-color: rgba(255, 255, 255, 0.15) !important;

  &:hover {
    border-color: var(--o-color-primary1) !important;
  }
}

[data-o-theme="e.dark"] .o-pagination-select .o-select-input,
.dark .o-pagination-select .o-select-input {
  color: var(--o-color-info1) !important;
}

[data-o-theme="e.dark"] .o_box-main,
.dark .o_box-main {
  background: #242427;
  border-color: rgba(255, 255, 255, 0.15);
}

[data-o-theme="e.dark"] .o_box-main .o_input-input,
.dark .o_box-main .o_input-input {
  color: var(--o-color-info1) !important;
}

.o-dropdown-item:hover {
  background: var(--o-color-control2-light);
}
</style>
