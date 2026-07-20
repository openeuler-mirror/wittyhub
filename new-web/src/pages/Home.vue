<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSkillStore } from '@/stores/skill'
import { useAppStore } from '@/stores/app'
import { OSelect, OOption } from '@opensig/opendesign'
import FilterSidebar from '@/components/FilterSidebar.vue'
import SkillCard from '@/components/SkillCard.vue'
import SkillListItem from '@/components/SkillListItem.vue'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'
import viewGridSvg from '@/assets/icons/view-grid.svg?raw'
import viewListSvg from '@/assets/icons/view-list.svg?raw'
import cardBgLight from '@/assets/bg/card-bg-light.png'
import cardBgDark from '@/assets/bg/card-bg-dark.png'

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

const pageSizeOptions = [20, 50, 100]

const totalPages = computed(() => skillStore.totalPages)

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

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  skillStore.setFilter('page', page)
  skillStore.fetchSkills()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function changePageSize(size: number) {
  skillStore.setFilter('pageSize', size)
  skillStore.setFilter('page', 1)
  skillStore.fetchSkills()
}

function getPageNumbers(): (number | string)[] {
  const pages: (number | string)[] = []
  const total = totalPages.value
  const current = skillStore.filter.page

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
    return pages
  }

  pages.push(1)

  if (current > 4) pages.push('...')

  const start = Math.max(2, current - 2)
  const end = Math.min(total - 1, current + 2)

  for (let i = start; i <= end; i++) pages.push(i)

  if (current < total - 3) pages.push('...')

  pages.push(total)

  return pages
}
</script>

<template>
  <div>
    <!-- Hero 区域 -->
    <section class="relative overflow-hidden" style="height: 319.2px">
      <!-- 设计稿背景图 -->
      <div class="absolute inset-0 pointer-events-none">
        <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" class="w-full h-full object-cover" />
      </div>

      <div class="container-wide relative h-full flex flex-col items-center justify-center text-center">
        <h1 class="text-4xl font-bold text-[var(--o-color-info1)] mb-3" style="font-family: HarmonyHeiTi">
          SkillHub
        </h1>
        <p class="text-[16px] leading-6 text-[var(--o-color-text3)] mb-2">
          探索、评价、贡献openEuler技能
        </p>
        <p class="text-sm leading-[22px] text-[var(--o-color-text3)] mb-8" style="font-family: HarmonyHeiTi">
          <span class="text-[var(--o-color-primary1)] font-medium">{{ skillStore.stats?.total_skills?.toLocaleString() || '200' }}+</span>
          Skills
          <span class="mx-2 text-[var(--o-color-text3)]">|</span>
          <span class="text-[var(--o-color-primary1)] font-medium">{{ skillStore.stats?.total_categories || '15' }}+</span>
          领域分类
        </p>

        <!-- 搜索框 -->
        <div style="max-width:620px; width:100%; margin:0 auto">
          <div class="relative">
            <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--o-color-text3)]" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>
              <path d="M16.5 16.5L21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <input
              v-model="searchInput"
              type="text"
              placeholder="搜索 Skill"
              class="w-full h-12 pl-12 pr-24 text-sm bg-white border border-[var(--o-color-control4)] rounded-lg shadow-sm focus:outline-none focus:border-[var(--o-color-primary1)] focus:ring-1 focus:ring-[var(--o-color-primary1)]/20 text-[var(--o-color-info1)] placeholder:text-[var(--o-color-text3)] dark:bg-gray-800 dark:border-gray-700"
              @keyup.enter="handleSearch"
            />
            <button
              @click="handleSearch"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 h-9 px-5 bg-[var(--o-color-primary1)] text-white text-sm rounded-md hover:bg-[var(--o-color-primary1)]/90 transition-colors"
            >
              搜索
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 主要内容区 -->
    <section class="container-wide py-6">
      <div class="flex gap-8">
        <!-- 左侧筛选侧栏 -->
        <div class="w-60 flex-shrink-0 hidden lg:block sticky top-[88px] self-start">
          <FilterSidebar />
        </div>

        <!-- 右侧内容区 -->
        <div class="flex-1 min-w-0">
          <!-- 搜索结果提示 -->
          <div v-if="isSearchPage && searchQuery" class="mb-4 text-sm text-[var(--o-color-text3)]">
            为您找到 <span class="text-[var(--o-color-primary1)] font-medium">{{ skillStore.total }}</span> 个与 "{{ searchQuery }}" 匹配的搜索结果
          </div>

          <!-- 工具栏 -->
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="switch-tab">
                <div
                  class="switch-tab-slider"
                  :class="{ 'slider-right': skillStore.filter.sortBy === 'latest' }"
                />
                <button
                  class="switch-handler"
                  :class="{ active: skillStore.filter.sortBy === 'hot' }"
                  @click="setSortBy('hot')"
                >
                  热门
                </button>
                <button
                  class="switch-handler"
                  :class="{ active: skillStore.filter.sortBy === 'latest' }"
                  @click="setSortBy('latest')"
                >
                  最新
                </button>
              </div>

              <OSelect
                v-if="skillStore.filter.sortBy !== 'latest'"
                size="medium"
                option-width-mode="width"
                :model-value="skillStore.filter.sortPeriod"
                @change="setSortPeriod"
              >
                <OOption
                  v-for="opt in sortOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </OSelect>
            </div>

            <div class="switch-tab">
              <div
                class="switch-tab-slider"
                :class="{ 'slider-right': skillStore.filter.viewMode === 'list' }"
              />
              <button
                class="switch-handler flex items-center justify-center"
                :class="{ active: skillStore.filter.viewMode === 'card' }"
                @click="setViewMode('card')"
                title="卡片视图"
              >
                <span class="w-5 h-5 flex items-center justify-center" v-html="viewGridSvg"></span>
              </button>
              <button
                class="switch-handler flex items-center justify-center"
                :class="{ active: skillStore.filter.viewMode === 'list' }"
                @click="setViewMode('list')"
                title="列表视图"
              >
                <span class="w-5 h-5 flex items-center justify-center" v-html="viewListSvg"></span>
              </button>
            </div>
          </div>

          <!-- 加载态 -->
          <div v-if="skillStore.loading" class="space-y-4">
            <div v-if="skillStore.filter.viewMode === 'card'" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              <div v-for="i in 6" :key="i" class="bg-white rounded-lg border border-[var(--o-color-control4)] p-3">
                <div class="h-5 bg-[var(--o-color-control6)] rounded w-3/4 mb-3 animate-pulse"></div>
                <div class="h-3 bg-[var(--o-color-control6)] rounded w-1/2 mb-3 animate-pulse"></div>
                <div class="h-10 bg-[var(--o-color-control6)] rounded mb-3 animate-pulse"></div>
                <div class="flex gap-1 mb-3">
                  <div class="h-5 w-12 bg-[var(--o-color-control6)] rounded animate-pulse"></div>
                  <div class="h-5 w-12 bg-[var(--o-color-control6)] rounded animate-pulse"></div>
                </div>
                <div class="h-4 bg-[var(--o-color-control6)] rounded w-full animate-pulse"></div>
              </div>
            </div>
            <div v-else class="space-y-2">
              <div v-for="i in 10" :key="i" class="bg-white rounded-lg border border-[var(--o-color-control4)] p-3">
                <div class="h-4 bg-[var(--o-color-control6)] rounded w-1/3 mb-2 animate-pulse"></div>
                <div class="h-3 bg-[var(--o-color-control6)] rounded w-2/3 animate-pulse"></div>
              </div>
            </div>
          </div>

          <!-- 空态 -->
          <div v-else-if="skillStore.skills.length === 0" class="text-center py-16">
            <svg class="w-16 h-16 mx-auto text-[var(--o-color-text3)] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <p class="text-[var(--o-color-text3)]">暂无相关 Skill</p>
          </div>

          <!-- Skill 列表 -->
          <template v-else>
            <div v-if="skillStore.filter.viewMode === 'card'" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              <SkillCard v-for="skill in skillStore.skills" :key="skill.id" :skill="skill" />
            </div>
            <div v-else class="border border-gray-200 rounded-lg dark:border-gray-700 overflow-hidden">
              <!-- 列表视图表头 -->
              <div class="flex items-center gap-4 px-4 py-2 border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 list-header" style="font-family: HarmonyHeiTi; font-size: 14px; line-height: 22px; font-weight: 600; letter-spacing: 0px;">
                <div class="flex-1 min-w-0">名称</div>
                <div class="hidden md:block w-24">分类</div>
                <div class="hidden sm:block w-20">风险等级</div>
                <div class="hidden sm:block w-20">下载量</div>
                <div class="hidden lg:block w-24">贡献者</div>
              </div>
              <SkillListItem v-for="skill in skillStore.skills" :key="skill.id" :skill="skill" />
            </div>

            <!-- 分页 -->
            <div class="flex items-center justify-between mt-8">
              <div class="text-sm text-[var(--o-color-text3)]">
                共 {{ skillStore.total }} 条数据
              </div>

              <div class="flex items-center gap-2">
                <select
                  :value="skillStore.filter.pageSize"
                  class="h-8 px-2 text-sm bg-white border border-[var(--o-color-control4)] rounded-md text-[var(--o-color-info1)] focus:outline-none focus:border-[var(--o-color-primary1)] dark:bg-gray-800 dark:border-gray-700"
                  @change="changePageSize(Number(($event.target as HTMLSelectElement).value))"
                >
                  <option v-for="size in pageSizeOptions" :key="size" :value="size">
                    {{ size }}条/页
                  </option>
                </select>

                <div class="flex items-center gap-1">
                  <!-- 上一页 -->
                  <button
                    class="w-8 h-8 flex items-center justify-center rounded-md border border-[var(--o-color-control4)] text-[var(--o-color-text3)] hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed dark:border-gray-700 dark:hover:bg-gray-800"
                    :disabled="skillStore.filter.page <= 1"
                    @click="changePage(skillStore.filter.page - 1)"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                    </svg>
                  </button>

                  <!-- 页码 -->
                  <template v-for="(page, idx) in getPageNumbers()" :key="idx">
                    <span v-if="page === '...'" class="w-8 h-8 flex items-center justify-center text-sm text-[var(--o-color-text3)]">...</span>
                    <button
                      v-else
                      class="w-8 h-8 text-sm rounded-md transition-colors"
                      :class="page === skillStore.filter.page
                        ? 'bg-[var(--o-color-primary1)] text-white'
                        : 'text-[var(--o-color-info1)] page-btn'"
                      @click="changePage(page as number)"
                    >
                      {{ page }}
                    </button>
                  </template>

                  <!-- 下一页 -->
                  <button
                    class="w-8 h-8 flex items-center justify-center rounded-md border border-[var(--o-color-control4)] text-[var(--o-color-text3)] hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed dark:border-gray-700 dark:hover:bg-gray-800"
                    :disabled="skillStore.filter.page >= totalPages"
                    @click="changePage(skillStore.filter.page + 1)"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                  </button>
                </div>

                <!-- 跳页 -->
                <div class="flex items-center gap-1 text-sm text-[var(--o-color-text3)]">
                  跳至
                  <input
                    type="number"
                    :value="skillStore.filter.page"
                    class="w-12 h-7 px-1 text-center border border-[var(--o-color-control4)] rounded-md focus:outline-none focus:border-[var(--o-color-primary1)] text-[var(--o-color-info1)] dark:bg-gray-800 dark:border-gray-700"
                    min="1"
                    :max="totalPages"
                    @keyup.enter="changePage(Number(($event.target as HTMLInputElement).value))"
                  />
                  页
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 提交新Skill区 -->
      <div class="mt-16 text-center">
        <h2 class="text-2xl font-bold text-[var(--o-color-info1)] mb-3">提交新Skill</h2>
        <p class="text-[var(--o-color-text3)]">在社区中贡献您的 Skill 文件，共建xxxx</p>
      </div>

      <div class="mt-8 overflow-hidden relative border border-[var(--o-color-control4)]">
        <img :src="appStore.isDark ? cardBgDark : cardBgLight" alt="" class="absolute inset-0 w-full h-full object-cover pointer-events-none" />
        <div class="relative p-8">
          <p class="text-sm text-[var(--o-color-text3)] mb-6">
            Fork <code class="px-1.5 py-0.5 bg-[var(--o-color-control6)] rounded text-xs">openeuler/wittyhub</code> 仓库并Clone到本地，提交单个Skill 或 Skill 仓库链接，待PR审核通过后入仓，同步至首屏展示。
          </p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <h3 class="font-medium text-[var(--o-color-info1)] mb-2">方式1</h3>
              <p class="text-sm text-[var(--o-color-text3)] mb-3">
                <span class="inline-flex items-center gap-1 text-[var(--o-color-primary1)]">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                  </svg>
                  提交单个Skill
                </span>
              </p>
              <p class="text-sm text-[var(--o-color-text3)]">
                在skills目录下创建user/skillname目录，包含Skill.md 文件和其他依赖文件。
              </p>
            </div>

            <div>
              <h3 class="font-medium text-[var(--o-color-info1)] mb-2">方式2</h3>
              <p class="text-sm text-[var(--o-color-text3)] mb-3">
                <span class="inline-flex items-center gap-1 text-[var(--o-color-primary1)]">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                  </svg>
                  提交Skill仓库链接，自动拉取Skill
                </span>
              </p>
              <div class="bg-[var(--o-color-fill1)] rounded-md p-3 text-xs font-mono text-[var(--o-color-text3)]">
                <div>在skill/skill-repo.yaml里填写你的repo。</div>
                <div class="mt-1 text-[var(--o-color-text3)] opacity-60"># personal repo</div>
                <div>- url: https://github.com/xxx/repoxxx</div>
                <div>&nbsp;&nbsp;name: xxx</div>
                <div>&nbsp;&nbsp;branch: main</div>
                <div class="text-[var(--o-color-text3)] opacity-60"># 一次提交多个</div>
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
  max-width: 1416px;
  margin: 0 auto;
  padding: 0 24px;
}

@media (max-width: 768px) {
  .container-wide {
    padding: 0 16px;
  }
}

/* 列表视图表头 */
.list-header {
  color: #000000CC;
}

[data-o-theme="e.dark"] .list-header,
.dark .list-header {
  color: #C9CDD4;
}

/* switch-tab: 滑块切换按钮组 (参考 openEuler portal switch-tab 模式) */
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
}

.switch-handler:not(.active):hover {
  color: var(--o-color-link1);
  background: var(--o-color-fill3);
}

.switch-handler.active {
  color: var(--o-color-link1);
  font-weight: 500;
}

/* OSelect 覆盖：与 switch-tab/筛选栏统一 */
:deep(.o-select) {
  --select-height: 32px;
  --select-radius: 4px;
  --select-text-size: 14px;
  width: 120px;
}

/* 分页按钮 hover 浅蓝 */
.page-btn:hover {
  background-color: color-mix(in srgb, var(--o-color-primary1) 20%, transparent);
}
</style>
