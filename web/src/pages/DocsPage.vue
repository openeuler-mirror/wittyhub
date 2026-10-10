<script setup lang="ts">
/**
 * 站内文档页（使用指南）：左侧「文档 + 章节」合并目录，右侧白色正文卡片 + 上下篇翻页。
 *
 * 版式对齐设计稿「使用指南示例」：
 * - 页标题 40/56 semibold、副标题 18/26（60% 黑，与贡献页副标题一致）；
 *   内容区与 AppHeader/风险评估报告页同宽（1488px + 24px padding），
 *   左缘对齐 header logo、右缘对齐用户图标；
 * - 左栏 272px：目录使用组件库 OMenu（arrowPosition=left，含 OSubMenu/OMenuItem），
 *   逐级缩进、引导线（#E0E2E6）、展开动画、hover 底色（control2-light）与
 *   选中路径高亮均由组件规范提供；行高/字号沿用设计稿（14px 文字、40px 行），
 *   当前章节为浅蓝底 + 左侧 2×32 蓝色指示条，当前文档与当前章节的上级为蓝色文字；
 *   含子章节的分组默认仅「当前章节所在分组」展开（设计稿形态），可手动折叠/展开；
 *   折叠箭头置于行首（文字左侧），收起朝下、展开朝上；箭头点击只切换展开/收起；
 *   分组行（文档行、含子章节的章节行）点击文字：跳转与"展开/收起切换"同时发生
 *   （展开→合并、合并→展开；与 openEuler 文档站目录行为一致）；
 *   目录项为原生 <a>（/docs/{doc}#{section}），左键交给路由、Cmd/Ctrl/中键可新标签打开；
 * - 右栏白卡：宽至 1412px、圆角 8、内边距 24/40/32，正文排版见
 *   MarkdownRenderer 的 docs 变体，正文下方 1px 分割线 + 上一篇/下一篇；
 * - 文档顺序即左栏顺序与翻页顺序，章节锚点 id 由正文渲染组件回传（doc-section-N / N-M）。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { OLoading, OMenu, OMenuItem, OSubMenu } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'
import MarkdownRenderer, { parseDocOutline, type OutlineItem } from '@/components/MarkdownRenderer.vue'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'

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

/** 手动展开/收起的目录项（key = `doc:${name}` 或 `${doc}::${sectionId}`；未记录时按默认规则） */
const manualExpanded = ref<Record<string, boolean>>({})

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
 * OMenu 目录项的 value/key。
 * 章节锚点 id（doc-section-N / N-M）在各文档间是重复的，必须带上文档名，
 * 否则其他文档的同名章节会被误判为高亮/选中。
 */
function docKey(doc: string) {
  return `doc:${doc}`
}

function sectionKey(doc: string, sectionId: string) {
  return `${doc}::${sectionId}`
}

/** OMenu 选中值：滚动联动到的当前章节；尚未联动到章节时回退到当前文档行 */
const menuActiveValue = computed(() =>
  docName.value && activeSectionId.value
    ? sectionKey(docName.value, activeSectionId.value)
    : docKey(docName.value)
)

/** 默认展开项：当前文档 + 当前章节所在分组（设计稿形态：当前分组展开、其余收起） */
const defaultExpandedKeys = computed(() => {
  const keys = new Set<string>()
  if (!docName.value) return keys
  keys.add(docKey(docName.value))
  activeIds.value.forEach((id) => keys.add(sectionKey(docName.value, id)))
  return keys
})

/** OMenu 展开数组：默认展开项叠加手动展开/收起结果（手动优先） */
const menuExpanded = computed(() => {
  const keys = new Set(defaultExpandedKeys.value)
  for (const [key, open] of Object.entries(manualExpanded.value)) {
    if (open) keys.add(key)
    else keys.delete(key)
  }
  return [...keys]
})

/**
 * 同步展开数组：与默认态（当前文档 + 当前章节所在分组）一致的项清除手动记录，
 * 保证滚动联动的默认规则仍生效；不一致的项记录为手动状态。
 * 供 OMenu 的 expanded-change（点箭头）与点击分组行文字的切换共用。
 */
function syncExpandedKeys(values: string[]) {
  const next = new Set(values)
  const manual: Record<string, boolean> = {}
  const keys = new Set([...next, ...defaultExpandedKeys.value])
  for (const key of keys) {
    if (next.has(key) !== defaultExpandedKeys.value.has(key)) manual[key] = next.has(key)
  }
  manualExpanded.value = manual
}

/**
 * 切换指定目录项的展开/收起（点击分组行文字时执行）。
 * 基于当前生效的展开数组计算，与跳转在同一次点击内同步完成，互不覆盖。
 */
function toggleMenuItem(key: string) {
  const keys = new Set(menuExpanded.value)
  if (keys.has(key)) keys.delete(key)
  else keys.add(key)
  syncExpandedKeys([...keys])
}

/**
 * 点击章节链接（叶子行）：统一交给路由处理（带 hash 的导航由 router.scrollBehavior 滚动到锚点，
 * 避免浏览器原生 hash 跳转被 scrollBehavior 拉回页面顶部）。
 * - 当前文档：同路由带 hash 跳转，锚点元素已存在，直接定位并立即高亮点击项；
 * - 其他文档：跳转到目标文档，正文渲染完成后由 scrollToHash 定位、refreshActiveSection 恢复高亮；
 * - 点击后锁定该章节高亮，避免"滚到底"等联动把高亮覆盖到其他目录项（用户再滚动时解除）；
 * - Cmd/Ctrl/中键等保持浏览器默认行为（新标签打开 href）。
 */
function handleSectionClick(e: MouseEvent, doc: string, sectionId: string) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
    e.stopPropagation()
    return
  }
  e.preventDefault()
  lockedSectionId = sectionId
  lockedDocName = doc
  const hash = `#${sectionId}`
  if (doc === docName.value) {
    activeSectionId.value = sectionId
    router.push({ hash })
  } else {
    router.push({ path: `/docs/${doc}`, hash })
  }
}

/**
 * 点击文档标题：跳转到该文档（当前文档会清掉 hash、滚回文档顶部），
 * 同时切换该文档下级目录的展开/收起（展开→合并、合并→展开）—— 跳转与切换同时发生。
 * 跳转目标是文档顶部，解除章节点击锁定，交回滚动联动；
 * 阻止冒泡：切换由 toggleMenuItem 统一执行，避免组件原生切换再叠加一次（两次切换等于没切）。
 * Cmd/Ctrl/中键等保持浏览器默认行为（新标签打开 href），同样阻止冒泡。
 */
function handleDocClick(e: MouseEvent, doc: string) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
    e.stopPropagation()
    return
  }
  e.preventDefault()
  e.stopPropagation()
  clearSectionLock()
  toggleMenuItem(docKey(doc))
  router.push(`/docs/${doc}`)
}

/** 点击含子章节的分组行：跳转到该章节，同时切换其下级目录的展开/收起（跳转与切换同时发生） */
function handleGroupSectionClick(e: MouseEvent, doc: string, sectionId: string) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
    e.stopPropagation()
    return
  }
  e.preventDefault()
  e.stopPropagation()
  toggleMenuItem(sectionKey(doc, sectionId))
  lockedSectionId = sectionId
  lockedDocName = doc
  const hash = `#${sectionId}`
  if (doc === docName.value) {
    activeSectionId.value = sectionId
    router.push({ hash })
  } else {
    router.push({ path: `/docs/${doc}`, hash })
  }
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

/**
 * 点击目录项后锁定的章节 id 及其所属文档。
 * 点击底部区域的目录项时，页面可能已经到底、无法把该标题滚到判定线以上，
 * 若继续按滚动位置联动（含"到底定位最后一项"）会把高亮错误地落到最后一个目录项，
 * 因此在用户再次主动滚动前，保持点击项高亮。
 */
let lockedSectionId = ''
let lockedDocName = ''

/** 解除点击锁定（用户重新滚动、或导航到目标文档之外时） */
function clearSectionLock() {
  lockedSectionId = ''
  lockedDocName = ''
}

/** 滚动联动：取最后一个已越过吸顶导航下沿的 h2/h3 作为当前章节 */
let ticking = false

function measureActiveSection() {
  ticking = false
  // 点击目录项后保持点击项高亮（含跨文档跳转），用户重新滚动时解除
  if (lockedSectionId) return
  if (!outline.value.length) return
  const headings = Array.from(
    document.querySelectorAll<HTMLElement>('.docs-card .markdown-body h2[id], .docs-card .markdown-body h3[id]')
  )
  if (!headings.length) return

  /*
   * 页面滚到底时，最后一个标题可能永远越不过判定线（页面高度不足、浏览器缩放/小屏时尤其明显），
   * 导致目录停在倒数第二个章节。此时直接定位到最后一个章节，保证与正文位置一致。
   * 取两种 scrollHeight 的最大值并留 2px 容差，兼容各浏览器与缩放产生的亚像素误差。
   */
  const scrollHeight = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight
  )
  const atBottom =
    scrollHeight > window.innerHeight + 1 &&
    window.innerHeight + window.scrollY >= scrollHeight - 2
  if (atBottom) {
    activeSectionId.value = headings[headings.length - 1].id
    return
  }

  // 吸顶导航 72px + 24px 间距，与正文 scroll-margin-top 保持一致
  const threshold = 97
  let current = headings[0].id
  for (const heading of headings) {
    if (heading.getBoundingClientRect().top <= threshold) current = heading.id
    else break
  }
  activeSectionId.value = current
}

/**
 * 刷新当前章节高亮（大纲就绪、切换文档等时机调用）：
 * 点击锁定期间恢复点击项高亮，否则按滚动位置联动。
 */
function refreshActiveSection() {
  ticking = false
  if (lockedSectionId) {
    activeSectionId.value = lockedSectionId
    return
  }
  measureActiveSection()
}

/** 用户主动滚动（滚轮/触摸/键盘）时解除点击锁定，恢复滚动联动与"到底高亮最后一项" */
function unlockActiveSection() {
  if (!lockedSectionId) return
  clearSectionLock()
  onScroll()
}

/** 会触发页面滚动的按键 */
const SCROLL_KEYS = new Set(['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '])

function onScrollKeydown(e: KeyboardEvent) {
  if (SCROLL_KEYS.has(e.key)) unlockActiveSection()
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
  // 窗口尺寸/缩放变化后重新计算高亮位置，避免停留在旧章节
  window.addEventListener('resize', onScroll, { passive: true })
  // 用户主动滚动时解除点击锁定（这些事件只来自用户操作，程序滚动不会触发）
  window.addEventListener('wheel', unlockActiveSection, { passive: true })
  window.addEventListener('touchmove', unlockActiveSection, { passive: true })
  window.addEventListener('keydown', onScrollKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
  window.removeEventListener('wheel', unlockActiveSection)
  window.removeEventListener('touchmove', unlockActiveSection)
  window.removeEventListener('keydown', onScrollKeydown)
})

// 章节大纲就绪（正文渲染完成）后刷新联动位置，并按需定位到 hash 指向的章节
watch(outline, async () => {
  await nextTick()
  refreshActiveSection()
  scrollToHash()
})

// 切换文档时清理其他文档的手动展开记录（避免目录越点越乱），
// 但保留本次目标文档的记录——点击分组行触发的展开/收起必须在跳转后仍然生效
watch(
  () => route.params.doc,
  async () => {
    const doc = docName.value
    // 锁定目标与本次导航的文档不一致（如浏览器后退/前进）时解除锁定，交回滚动联动
    if (lockedSectionId && lockedDocName !== doc) clearSectionLock()
    manualExpanded.value = Object.fromEntries(
      Object.entries(manualExpanded.value).filter(
        ([key]) => key === docKey(doc) || key.startsWith(`${doc}::`)
      )
    )
    await loadDoc()
    await nextTick()
    refreshActiveSection()
    scrollToHash()
  }
)
</script>

<template>
  <div class="docs-page">
    <!-- 顶部纹理：与贡献页面一致——同一套 hero 纹理（light/dark 双图，object-cover 绝对定位铺满） -->
    <div class="hero-texture">
      <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" />
    </div>

    <div class="docs-container">
      <h1 class="page-title">使用指南</h1>
      <p class="page-desc">了解平台能力、发布流程与安全评估</p>

      <div class="docs-layout">
        <!-- ========== 左：文档 + 章节目录 ========== -->
        <aside class="docs-sidebar">
          <OMenu
            class="docs-menu"
            arrow-position="left"
            :model-value="menuActiveValue"
            :expanded="menuExpanded"
            @expanded-change="syncExpandedKeys"
          >
            <OSubMenu v-for="doc in docs" :key="doc.name" :value="docKey(doc.name)">
              <template #title>
                <a
                  class="menu-link"
                  :href="`/docs/${doc.name}`"
                  @click="handleDocClick($event, doc.name)"
                >
                  {{ doc.title }}
                </a>
              </template>

              <template v-for="section in doc.outline" :key="section.id">
                <!-- 含小节的章节：二级分组（可折叠），点击标题跳转到该章节并展开下级目录 -->
                <OSubMenu v-if="section.children.length" :value="sectionKey(doc.name, section.id)">
                  <template #title>
                    <a
                      class="menu-link"
                      :href="`/docs/${doc.name}#${section.id}`"
                      @click="handleGroupSectionClick($event, doc.name, section.id)"
                    >
                      {{ section.text }}
                    </a>
                  </template>
                  <OMenuItem
                    v-for="child in section.children"
                    :key="child.id"
                    :value="sectionKey(doc.name, child.id)"
                  >
                    <a
                      class="menu-link"
                      :href="`/docs/${doc.name}#${child.id}`"
                      @click="handleSectionClick($event, doc.name, child.id)"
                    >
                      {{ child.text }}
                    </a>
                  </OMenuItem>
                </OSubMenu>

                <!-- 无小节的章节：叶子项 -->
                <OMenuItem v-else :value="sectionKey(doc.name, section.id)">
                  <a
                    class="menu-link"
                    :href="`/docs/${doc.name}#${section.id}`"
                    @click="handleSectionClick($event, doc.name, section.id)"
                  >
                    {{ section.text }}
                  </a>
                </OMenuItem>
              </template>
            </OSubMenu>
          </OMenu>
        </aside>

        <!-- ========== 右：正文卡片 ========== -->
        <div class="docs-main">
          <div class="docs-card">
            <div v-if="loading" class="state-block">
              <OLoading :visible="true" size="medium" :mask="false" />
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

/* ===== 顶部纹理：与贡献页面一致，hero 纹理 object-cover 绝对定位铺满（light/dark 各一张） ===== */
.hero-texture {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  /* 可见区高 183px：覆盖页头下方至标题（h1）底边 */
  height: 183px;
  overflow: hidden;
  pointer-events: none;

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

/* 与 AppHeader 的 ContentWrapper 同宽（1488px + 24px padding）、与风险报告页一致：
   左缘对齐 header logo、右缘对齐右上角用户图标，内容不超出页头宽度 */
.docs-container {
  position: relative;
  box-sizing: border-box;
  max-width: 1488px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ===== 页标题：40/56 semibold，距页头 48px；副标题 18/26（80% 黑） =====
   行高用令牌（首页 hero 标题同样写法） */
.page-title {
  margin: 0;
  padding-top: 48px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: var(--o-font_size-display3);
  line-height: var(--o-line_height-display3);
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
  /* 与贡献页副标题（.hero-subtitle，info3）保持一致 */
  color: var(--o-color-info3);
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

/* ===== 左侧目录（OpenDesign OMenu，arrowPosition=left）：
   层级缩进、引导线、展开动画、hover 底色与选中路径高亮均由组件规范提供；
   行高/字号沿用设计稿（14px 文字、40px 行），hover 底色用组件令牌 control2-light ===== */
.docs-menu {
  --menu-width: 100%;
  --menu-bg-color: transparent;
  --menu-item-padding-v: 8px;
  --menu-padding-h: 8px;
  --menu-text-size: var(--o-font_size-text1);
  --menu-text-height: var(--o_line_height-text1);
  /* 引导线：浅色用设计稿定值（深色见下方令牌覆盖） */
  --menu-indicator-bg-color: #{$guide-color};

  /* medium 档在 ≤1680px 会把一级项文字压到 tip1，这里按设计稿保持 text1 */
  :deep(.o-sub-menu[data-level='0'] > .o-sub-menu-title),
  :deep(.o-menu-item[data-level='0']) {
    --menu-text-size: var(--o-font_size-text1);
    --menu-text-height: var(--o_line_height-text1);
  }

  /* 目录行：设计稿 40px 行高 */
  :deep(.o-sub-menu-title),
  :deep(.o-menu-item) {
    position: relative;
    min-height: 40px;
  }

  /* 行内容区撑满行宽、允许自然换行（组件默认内容自适应宽且 2 行截断，与设计稿不符） */
  :deep(.o-sub-menu-title-content),
  :deep(.o-menu-item-content) {
    flex: 1;
    margin-right: 0;
    display: block;
    overflow: visible;
    word-break: break-word;
  }

  /* 当前章节为二级分组（含子项）时同样给浅蓝底（组件默认仅叶节点有底色） */
  :deep(.o-sub-menu-selected > .o-sub-menu-title) {
    background-color: var(--menu-bg-color-selected);
  }

  /* 当前章节：左侧 2×32 蓝色指示条（设计稿） */
  :deep(.o-menu-item-selected)::before,
  :deep(.o-sub-menu-selected > .o-sub-menu-title)::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    transform: translateY(-50%);
    width: 2px;
    height: 32px;
    border-radius: 1px;
    background: var(--o-color-primary1);
  }
}

/* 目录链接：保留原生 <a> 语义（支持新标签打开），占满行内容区宽度；
   行高、hover/选中底色由目录行负责 */
.menu-link {
  display: block;
  color: inherit;
  text-decoration: none;
}

/* 深色模式下页面底色交回站点（设计稿仅提供浅色参考） */
[data-o-theme='e.dark'] .docs-page {
  background: transparent;
}

/* 深色模式下引导线改用令牌（设计稿浅色值在深色底上过亮） */
[data-o-theme='e.dark'] .docs-menu {
  --menu-indicator-bg-color: var(--o-color-control4);
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