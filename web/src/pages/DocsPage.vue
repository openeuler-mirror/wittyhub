<script setup lang="ts">
/**
 * 站内文档页（使用指南）：左侧「文档 + 章节」合并目录，右侧白色正文卡片 + 上下篇翻页。
 *
 * 版式对齐设计稿「使用指南示例」（1920 画布）：
 * - 页标题 48/64 semibold、副标题 18/26（80% 黑），内容区左右边距 64px；
 * - 左栏 272px：文档行与章节行均 40px 高（8px 上下内边距 + 24px 行高），
 *   逐级缩进 21/16px，引导线 #E0E2E6；当前章节为浅蓝底（#CEDBF5，圆角 4）
 *   加左侧 2×32 蓝色指示条，当前文档与当前章节的上级为蓝色 medium 文字；
 *   含子章节的分组默认仅「当前章节所在分组」展开（设计稿形态），可手动折叠/展开；
 * - 右栏白卡：宽至 1412px、圆角 8、内边距 24/40/32，正文排版见
 *   MarkdownRenderer 的 docs 变体，正文下方 1px 分割线 + 上一篇/下一篇；
 * - 文档顺序即左栏顺序与翻页顺序，章节锚点 id 由正文渲染组件回传（doc-section-N / N-M）。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { OLoading } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'
import MarkdownRenderer, { parseDocOutline, type OutlineItem } from '@/components/MarkdownRenderer.vue'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/docs-hero-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'
import chevronDownSvg from '@/assets/icons/chevron-down.svg?raw'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

/** 文档顺序：左栏顺序与上下篇翻页顺序一致 */
const DOC_NAMES = ['skillhub-introduction', 'skillhub-publish-and-manage', 'skillhub-security-audit']

/** 左栏短标题：文档 H1 过长时用它替代（正文标题仍用文档原标题） */
const SHORT_TITLES: Record<string, string> = {
  'skillhub-security-audit': '安全评估',
}

interface DocNavItem {
  name: string
  title: string
  outline: OutlineItem[]
}

/** 左栏文档列表（标题与章节大纲随文档一起加载） */
const docs = ref<DocNavItem[]>(
  DOC_NAMES.map((name) => ({ name, title: SHORT_TITLES[name] || name, outline: [] }))
)

const content = ref('')
const loading = ref(true)
const error = ref('')

/** 当前正文章节大纲（由正文渲染组件回传，与左栏共用同一套锚点 id） */
const outline = ref<OutlineItem[]>([])

/** 滚动联动到的章节 id（当前章节） */
const activeSectionId = ref('')

/** 文档行折叠态：默认全部展开（与设计稿一致） */
const collapsedDocs = ref<Record<string, boolean>>({})

/** 含子章节的章节行折叠态（key = `${doc}::${sectionId}`，章节 id 在各文档间重复，必须带文档名） */
const collapsedSections = ref<Record<string, boolean>>({})

/** 路由参数只允许字母/数字/连字符，避免路径穿越 */
const docName = computed(() => String(route.params.doc || '').replace(/[^a-zA-Z0-9-]/g, ''))

/** 当前文档在文档顺序中的位置（用于上下篇） */
const currentIndex = computed(() => DOC_NAMES.indexOf(docName.value))

const prevDoc = computed(() =>
  currentIndex.value > 0 ? docs.value[currentIndex.value - 1] : null
)

const nextDoc = computed(() =>
  currentIndex.value >= 0 && currentIndex.value < docs.value.length - 1
    ? docs.value[currentIndex.value + 1]
    : null
)

/** 高亮路径：当前章节 +（当前章节为 h3 时）其所属 h2 */
const activeIds = computed(() => {
  const ids = new Set<string>()
  if (!activeSectionId.value) return ids
  ids.add(activeSectionId.value)
  const parent = outline.value.find((item) =>
    item.children.some((child) => child.id === activeSectionId.value)
  )
  if (parent) ids.add(parent.id)
  return ids
})

/**
 * 是否处于高亮路径中。
 * 章节锚点 id（doc-section-N / N-M）在各文档间是重复的，必须同时比对文档名，
 * 否则其他文档的同名章节会被误高亮。
 */
function isActiveSection(doc: string, sectionId: string) {
  return doc === docName.value && activeIds.value.has(sectionId)
}

/** 是否为滚动联动到的当前章节（同样需比对文档名，避免 id 跨文档重复误判） */
function isCurrentSection(doc: string, sectionId: string) {
  return doc === docName.value && activeSectionId.value === sectionId
}

/**
 * 点击章节链接：统一交给路由处理（带 hash 的导航由 router.scrollBehavior 滚动到锚点，
 * 避免浏览器原生 hash 跳转被 scrollBehavior 拉回页面顶部）。
 * - 当前文档：同路由带 hash 跳转，锚点元素已存在，直接定位；
 * - 其他文档：跳转到目标文档，正文异步渲染完成后由 scrollToHash 定位；
 * - Cmd/Ctrl/中键等保持浏览器默认行为（新标签打开 href）。
 */
function handleSectionClick(e: MouseEvent, doc: string, sectionId: string) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
  e.preventDefault()
  const hash = `#${sectionId}`
  if (doc === docName.value) router.push({ hash })
  else router.push({ path: `/docs/${doc}`, hash })
}

function toggleDoc(name: string) {
  collapsedDocs.value[name] = !collapsedDocs.value[name]
}

/** 章节折叠态的存储 key：章节 id 在各文档间是重复的，必须带上文档名 */
function sectionKey(doc: string, sectionId: string) {
  return `${doc}::${sectionId}`
}

/**
 * 章节分组是否展开：
 * - 手动切换过：以手动状态为准；
 * - 否则仅「当前章节所在分组」展开（设计稿形态：当前分组展开、其余收起）。
 */
function isSectionExpanded(doc: string, sectionId: string) {
  const manual = collapsedSections.value[sectionKey(doc, sectionId)]
  if (manual !== undefined) return !manual
  return isActiveSection(doc, sectionId)
}

function toggleSection(doc: string, sectionId: string) {
  collapsedSections.value[sectionKey(doc, sectionId)] = isSectionExpanded(doc, sectionId)
}

/** 左栏目录：读取每篇文档，取 H1 作标题、h2/h3 作章节大纲 */
async function loadDocs() {
  const items = await Promise.all(
    DOC_NAMES.map(async (name) => {
      try {
        const response = await fetch(`/docs/${name}.md`)
        if (!response.ok) throw new Error(String(response.status))
        const source = await response.text()
        const h1 = source.match(/^#\s+(.+)$/m)
        return {
          name,
          title: SHORT_TITLES[name] || (h1 ? h1[1].trim() : name),
          outline: parseDocOutline(source),
        }
      } catch {
        return { name, title: SHORT_TITLES[name] || name, outline: [] }
      }
    })
  )
  docs.value = items
}

async function loadDoc() {
  loading.value = true
  error.value = ''
  // 切换文档时先清空上一篇章的大纲与联动状态，避免加载失败时残留旧目录
  outline.value = []
  activeSectionId.value = ''
  try {
    const response = await fetch(`/docs/${docName.value}.md`)
    if (!response.ok) throw new Error(String(response.status))
    content.value = await response.text()
    oaReport('doc_view', { module: 'docs', doc: docName.value })
  } catch (e) {
    console.error('加载文档失败:', e)
    content.value = ''
    error.value = '文档不存在或加载失败'
  } finally {
    loading.value = false
  }
}

/** 滚动联动：取最后一个已越过吸顶导航下沿的 h2/h3 作为当前章节 */
let ticking = false

function measureActiveSection() {
  ticking = false
  if (!outline.value.length) return
  const headings = Array.from(
    document.querySelectorAll<HTMLElement>('.docs-card .markdown-body h2[id], .docs-card .markdown-body h3[id]')
  )
  if (!headings.length) return
  // 吸顶导航 72px + 24px 间距，与正文 scroll-margin-top 保持一致
  const threshold = 97
  let current = headings[0].id
  for (const heading of headings) {
    if (heading.getBoundingClientRect().top <= threshold) current = heading.id
    else break
  }
  activeSectionId.value = current
}

function onScroll() {
  if (ticking) return
  ticking = true
  window.requestAnimationFrame(measureActiveSection)
}

/** 带 hash 进入（跨文档点章节、或直接打开带 hash 的链接）时，正文渲染完成后定位到该章节 */
function scrollToHash() {
  const id = decodeURIComponent(route.hash.replace(/^#/, ''))
  if (!id) return
  document.getElementById(id)?.scrollIntoView()
}

onMounted(() => {
  loadDocs()
  loadDoc()
  window.addEventListener('scroll', onScroll, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
})

// 章节大纲就绪（正文渲染完成）后刷新联动位置，并按需定位到 hash 指向的章节
watch(outline, async () => {
  await nextTick()
  measureActiveSection()
  scrollToHash()
})

// 切换文档时展开其所属文档行，并重新解析正文与联动位置
watch(
  () => route.params.doc,
  async () => {
    collapsedDocs.value[docName.value] = false
    await loadDoc()
    await nextTick()
    measureActiveSection()
    scrollToHash()
  }
)
</script>

<template>
  <div class="docs-page">
    <!-- 顶部纹理：设计稿「使用指南示例」页头下方底纹（椭圆 + 波纹 + 左侧光带，1x 1920x183） -->
    <div class="hero-texture">
      <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" />
    </div>

    <div class="docs-container">
      <h1 class="page-title">使用指南</h1>
      <p class="page-desc">了解平台能力、发布流程与安全评估</p>

      <div class="docs-layout">
        <!-- ========== 左：文档 + 章节目录 ========== -->
        <aside class="docs-sidebar">
          <nav class="sidebar-nav">
            <div v-for="doc in docs" :key="doc.name" class="nav-doc">
              <div class="nav-row nav-row--doc" :class="{ 'is-active': doc.name === docName }">
                <router-link class="nav-doc-link" :to="`/docs/${doc.name}`">
                  {{ doc.title }}
                </router-link>
                <button
                  type="button"
                  class="nav-toggle"
                  :aria-expanded="!collapsedDocs[doc.name]"
                  :aria-label="`${collapsedDocs[doc.name] ? '展开' : '收起'}${doc.title}的章节`"
                  @click="toggleDoc(doc.name)"
                >
                  <span
                    class="nav-chevron"
                    :class="{ 'is-expanded': !collapsedDocs[doc.name] }"
                    v-html="chevronDownSvg"
                  ></span>
                </button>
              </div>

              <div v-show="!collapsedDocs[doc.name]" class="nav-sections">
                <div v-for="section in doc.outline" :key="section.id" class="nav-section">
                  <div
                    class="nav-row nav-row--section"
                    :class="{
                      'is-active': isActiveSection(doc.name, section.id),
                      'is-current': isCurrentSection(doc.name, section.id),
                    }"
                  >
                    <a
                      class="nav-link"
                      :href="`/docs/${doc.name}#${section.id}`"
                      @click="handleSectionClick($event, doc.name, section.id)"
                    >
                      {{ section.text }}
                    </a>
                    <button
                      v-if="section.children.length"
                      type="button"
                      class="nav-toggle"
                      :aria-expanded="isSectionExpanded(doc.name, section.id)"
                      :aria-label="`${isSectionExpanded(doc.name, section.id) ? '收起' : '展开'}${section.text}的小节`"
                      @click="toggleSection(doc.name, section.id)"
                    >
                      <span
                        class="nav-chevron"
                        :class="{ 'is-expanded': isSectionExpanded(doc.name, section.id) }"
                        v-html="chevronDownSvg"
                      ></span>
                    </button>
                  </div>

                  <div
                    v-if="section.children.length && isSectionExpanded(doc.name, section.id)"
                    class="nav-subs"
                  >
                    <div
                      v-for="child in section.children"
                      :key="child.id"
                      class="nav-row nav-row--sub"
                      :class="{
                        'is-active': isActiveSection(doc.name, child.id),
                        'is-current': isCurrentSection(doc.name, child.id),
                      }"
                    >
                      <a
                        class="nav-link"
                        :href="`/docs/${doc.name}#${child.id}`"
                        @click="handleSectionClick($event, doc.name, child.id)"
                      >
                        {{ child.text }}
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </nav>
        </aside>

        <!-- ========== 右：正文卡片 ========== -->
        <div class="docs-main">
          <div class="docs-card">
            <div v-if="loading" class="state-block">
              <OLoading v-model:visible="loading" size="medium" />
            </div>

            <div v-else-if="error" class="state-block">
              <p class="error-text">{{ error }}</p>
              <router-link class="back-link" to="/">返回首页</router-link>
            </div>

            <template v-else>
              <MarkdownRenderer v-model:outline="outline" variant="docs" :source="content" />

              <!-- 上下篇翻页：正文下方 1px 分割线，右侧「标题 下一篇 →」（设计稿） -->
              <nav v-if="prevDoc || nextDoc" class="docs-pager">
                <router-link
                  v-if="prevDoc"
                  class="pager-link pager-link--prev"
                  :to="`/docs/${prevDoc.name}`"
                >
                  <svg class="pager-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M3.25 12h17.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                    <path
                      d="M15.75 5.8 20.75 12 15.75 18.2"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  <span class="pager-label">上一篇</span>
                  <span class="pager-title">{{ prevDoc.title }}</span>
                </router-link>

                <router-link
                  v-if="nextDoc"
                  class="pager-link pager-link--next"
                  :to="`/docs/${nextDoc.name}`"
                >
                  <span class="pager-title">{{ nextDoc.title }}</span>
                  <span class="pager-label">下一篇</span>
                  <svg class="pager-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M3.25 12h17.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                    <path
                      d="M15.75 5.8 20.75 12 15.75 18.2"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </router-link>
              </nav>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
/* 左栏引导线颜色：设计稿定值（无对应 token） */
$guide-color: #e0e2e6;

.docs-page {
  position: relative;
  min-height: 100vh;
  /* 与页脚间距由 AppFooter 自带的 margin-top: 72px 提供（设计稿：卡片底 1999 -> 页脚 2071） */
  padding-bottom: 0;
  /* 设计稿页面底色 #F4F5F7（站点令牌 #F5F6F8 差 1 级）；本页与顶部底纹同色，避免纹理下沿出现分界线 */
  background: #f4f5f7;
}

/* ===== 顶部纹理：设计稿页头下方底纹 1920x183（1x），等比例铺满宽度 ===== */
.hero-texture {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  /* 设计稿底纹可见区高 183px（页头 72px 下方至 y=255） */
  height: 183px;
  overflow: hidden;
  pointer-events: none;

  img {
    display: block;
    width: 100%;
    height: auto;
  }
}

/* 设计稿：内容区左右边距 64px（1920 画布），超宽屏下整体居中 */
.docs-container {
  position: relative;
  box-sizing: border-box;
  max-width: 1920px;
  margin: 0 auto;
  padding: 0 64px;
}

/* ===== 页标题：48/64 semibold，距页头 48px；副标题 18/26（80% 黑） =====
   行高用设计稿定值（首页 hero 标题同样写法），避免 var() 行高在当前构建下不生效 */
.page-title {
  margin: 0;
  padding-top: 48px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: var(--o-font_size-display2);
  line-height: 64px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.page-desc {
  margin: 12px 0 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text2);
  line-height: 26px;
  letter-spacing: 0px;
  color: var(--o-color-info2);
}

/* ===== 左栏 272px + 右栏白卡（设计稿：栏间距 32px、与标题区间距 72px） ===== */
.docs-layout {
  display: flex;
  align-items: flex-start;
  gap: 32px;
  margin-top: 72px;
}

.docs-sidebar {
  position: sticky;
  /* 避开顶部 72px 吸顶导航，再留 24px 间距 */
  top: 96px;
  box-sizing: border-box;
  flex-shrink: 0;
  width: 272px;
  /* 目录超长时栏内滚动，滚动条不显示（设计稿无滚动条） */
  max-height: calc(100vh - 128px);
  overflow-y: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

/* ===== 目录行：统一 8px 上下内边距 + 24px 行高（40px），文字距行左 4px ===== */
.nav-row {
  position: relative;
  display: flex;
  align-items: center;
  box-sizing: border-box;
  min-height: 40px;
  padding: 8px 4px;
  border-radius: 8px;
  transition: background-color 0.15s;

  @include hover {
    background: var(--o-color-fill1);
  }
}

.nav-doc-link,
.nav-link {
  flex: 1;
  min-width: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text1);
  line-height: var(--o_line_height-text1);
  letter-spacing: 0px;
  color: var(--o-color-info2);
  text-decoration: none;
  transition: color 0.15s;

  @include hover {
    color: var(--o-color-primary1);
  }
}

/* 当前文档 / 当前章节路径：蓝色 medium（设计稿） */
.nav-row.is-active {
  .nav-doc-link,
  .nav-link {
    font-weight: var(--o-font_weight-medium);
    color: var(--o-color-primary1);
  }
}

/* 滚动到的当前章节：浅蓝底 + 左侧 2×32 蓝色指示条（设计稿） */
.nav-row.is-current {
  border-radius: 4px;
  background: var(--o-color-control3-light);

  &::before {
    content: '';
    position: absolute;
    left: -5px;
    top: 50%;
    transform: translateY(-50%);
    width: 2px;
    height: 32px;
    border-radius: 1px;
    background: var(--o-color-primary1);
  }
}

/* 章节（h2）：左缩进 21px，引导线位于 x=80（设计稿：行左 16px） */
.nav-sections {
  margin-left: 16px;
  padding-left: 4px;
  border-left: 1px solid $guide-color;
}

/* 子章节（h3）：再缩进 16px，引导线位于 x=97（设计稿：行左 101） */
.nav-subs {
  margin-left: 12px;
  padding-left: 3px;
  border-left: 1px solid $guide-color;
}

/* 深色模式下页面底色交回站点（设计稿仅提供浅色参考） */
[data-o-theme='e.dark'] .docs-page {
  background: transparent;
}

/* 深色模式下引导线改用令牌（设计稿浅色值在深色底上过亮） */
[data-o-theme='e.dark'] .nav-sections,
[data-o-theme='e.dark'] .nav-subs {
  border-left-color: var(--o-color-control4);
}

/* 折叠箭头：收起朝下，展开朝上；距行右 4px（设计稿） */
.nav-toggle {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--o-color-info2);
  cursor: pointer;
  transition: color 0.15s;

  @include hover {
    color: var(--o-color-primary1);
  }
}

.nav-chevron {
  display: inline-flex;
  transition: transform 0.15s;

  &.is-expanded {
    transform: rotate(180deg);
  }

  :deep(svg) {
    width: 24px;
    height: 24px;
  }
}

/* ===== 正文卡片：白色、圆角 8、内边距 24/40/32，宽至 1412px（设计稿） ===== */
.docs-main {
  flex: 1;
  min-width: 0;
}

.docs-card {
  box-sizing: border-box;
  max-width: 1412px;
  padding: 24px 40px 32px;
  border-radius: 8px;
  background: var(--o-color-fill2);
}

.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 240px;
}

.error-text {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-size: 16px;
  line-height: 24px;
  color: var(--o-color-danger1);
}

.back-link {
  font-family: HarmonyHeiTi;
  font-size: 14px;
  line-height: 22px;
  color: var(--o-color-link1);

  &:hover {
    color: var(--o-color-link2);
  }
}

/* ===== 上下篇翻页：1px 分割线 + 右侧「标题 下一篇 →」（设计稿） ===== */
.docs-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 72px;
  padding-top: 32px;
  border-top: 1px solid var(--o-color-control4);
}

.pager-link {
  display: inline-flex;
  align-items: center;
  font-family: HarmonyHeiTi;
  color: var(--o-color-primary1);
  text-decoration: none;

  @include hover {
    color: var(--o-color-link2);
  }
}

.pager-link--next {
  margin-left: auto;
}

.pager-title {
  font-size: var(--o-font_size-text1);
  line-height: var(--o_line_height-text1);
}

.pager-label {
  font-size: var(--o-font_size-tip1);
  line-height: var(--o_line_height-tip1);
}

/* 标题与「上一篇/下一篇」间距 16px，标签与箭头间距 8px（设计稿） */
.pager-link--next {
  .pager-label {
    margin-left: 16px;
  }

  .pager-arrow {
    margin-left: 8px;
  }
}

.pager-link--prev {
  .pager-label {
    margin-left: 8px;
  }

  .pager-title {
    margin-left: 16px;
  }
}

.pager-arrow {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
}

.pager-link--prev .pager-arrow {
  transform: rotate(180deg);
}
</style>