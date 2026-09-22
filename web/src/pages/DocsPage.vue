<script setup lang="ts">
/**
 * 站内文档页：左侧文档目录（三篇文档 + 当前文档标题大纲），右侧渲染正文。
 *
 * 文档源文件位于仓库 `docs/`，发布时同步一份到 `web/public/docs/`（web 镜像只打包
 * web/ 目录），页面按路由参数 `:doc` 取 `/docs/{doc}.md`，正文的解析、排版与站内
 * 互链改写由 `@/components/MarkdownRenderer.vue` 承接并回传章节大纲。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { OLoading, OAnchor, OAnchorItem, OIconChevronRight } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'
import MarkdownRenderer, { type OutlineItem } from '@/components/MarkdownRenderer.vue'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'

const route = useRoute()
const appStore = useAppStore()

/** 侧栏导航分组：分类 → 文档（顺序即侧栏展示顺序，文档需与 web/public/docs 下已同步的一致） */
interface DocGroup {
  title: string
  items: string[]
}
const DOC_GROUPS: DocGroup[] = [
  { title: '了解 SkillHub', items: ['skillhub-introduction'] },
  { title: '发布与管理 Skill', items: ['skillhub-publish-and-manage'] },
  { title: '安全与合规', items: ['skillhub-security-audit'] },
]

/** 全部文档名（用于批量读取标题） */
const DOC_NAMES = DOC_GROUPS.flatMap((group) => group.items)

/** 侧栏短标题：文档 H1 过长时用它替代，正文与面包屑仍用文档原标题 */
const SHORT_TITLES: Record<string, string> = {
  'skillhub-security-audit': '安全评估',
}

const content = ref('')
const loading = ref(true)
const error = ref('')

/** 章节大纲：由正文渲染组件解析后回传（右侧「本内容」目录使用） */
const outline = ref<OutlineItem[]>([])

/** 文档标题表：由各文档 H1 读出 */
const docTitles = ref<Record<string, string>>({})

/** 侧栏导航结构：分组 + 组内文档标题 */
const navGroups = computed(() =>
  DOC_GROUPS.map((group) => ({
    title: group.title,
    docs: group.items.map((name) => ({ name, title: docTitles.value[name] || name })),
  }))
)

/** 分组折叠态：默认全部展开（与参考站一致） */
const collapsed = ref<Record<string, boolean>>({})

function toggleGroup(title: string) {
  collapsed.value[title] = !collapsed.value[title]
}

/** 路由参数只允许字母/数字/连字符，避免路径穿越 */
const docName = computed(() => String(route.params.doc || '').replace(/[^a-zA-Z0-9-]/g, ''))

/** 侧栏标题：读取每篇文档的 H1（有短标题配置时优先用短标题） */
async function loadDocTitles() {
  const entries = await Promise.all(
    DOC_NAMES.map(async (name) => {
      const short = SHORT_TITLES[name]
      if (short) return [name, short] as const
      try {
        const response = await fetch(`/docs/${name}.md`)
        if (!response.ok) throw new Error(String(response.status))
        const match = (await response.text()).match(/^#\s+(.+)$/m)
        return [name, match ? match[1].trim() : name] as const
      } catch {
        return [name, name] as const
      }
    })
  )
  docTitles.value = Object.fromEntries(entries)
}

async function loadDoc() {
  loading.value = true
  error.value = ''
  // 切换文档时先清空上一篇章的大纲，避免加载失败时残留旧目录
  outline.value = []
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

onMounted(() => {
  loadDocTitles()
  loadDoc()
})

// 切换文档时展开其所属分组，避免当前文档落在收起的分组里
watch(() => route.params.doc, () => {
  const group = DOC_GROUPS.find((item) => item.items.includes(docName.value))
  if (group) collapsed.value[group.title] = false
  loadDoc()
})
</script>

<template>
  <div class="docs-page">
    <!-- 顶部纹理（与详情页/报告页同一张 hero 底纹） -->
    <div class="hero-texture">
      <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" />
    </div>

    <div class="container-wide">
      <h1 class="page-title">使用文档</h1>

      <div class="docs-layout">
        <!-- ========== 左：文档导航 ========== -->
        <aside class="docs-sidebar">
          <p class="panel-title">文档导航</p>
          <nav class="sidebar-nav">
            <div v-for="group in navGroups" :key="group.title" class="nav-group">
              <button
                type="button"
                class="nav-group-toggle"
                :aria-expanded="!collapsed[group.title]"
                @click="toggleGroup(group.title)"
              >
                <OIconChevronRight
                  class="nav-group-chevron"
                  :class="{ 'is-expanded': !collapsed[group.title] }"
                />
                <span>{{ group.title }}</span>
              </button>
              <ul v-show="!collapsed[group.title]" class="nav-group-items">
                <li v-for="doc in group.docs" :key="doc.name">
                  <router-link
                    class="sidebar-link"
                    :class="{ 'is-active': doc.name === docName }"
                    :to="`/docs/${doc.name}`"
                  >
                    {{ doc.title }}
                  </router-link>
                </li>
              </ul>
            </div>
          </nav>
        </aside>

        <!-- ========== 中：正文（整篇文档含标题一起渲染，解析与排版由渲染组件承接） ========== -->
        <div class="docs-main">
          <div v-if="loading" class="docs-card state-card">
            <OLoading v-model:visible="loading" size="medium" />
          </div>

          <div v-else-if="error" class="docs-card state-card">
            <p class="error-text">{{ error }}</p>
            <router-link class="back-link" to="/">返回首页</router-link>
          </div>

          <div v-else class="docs-card">
            <MarkdownRenderer v-model:outline="outline" :source="content" />
          </div>
        </div>

        <!-- ========== 右：本内容（页内目录，随正文滚动联动） ========== -->
        <aside v-if="!loading && outline.length" class="docs-toc">
          <p class="panel-title">本内容</p>
          <OAnchor
            :key="docName"
            class="toc-anchor"
            :target-offset="96"
            :change-hash="false"
          >
            <OAnchorItem
              v-for="item in outline"
              :key="item.id"
              :href="`#${item.id}`"
              :title="item.text"
            >
              <OAnchorItem
                v-for="child in item.children"
                :key="child.id"
                :href="`#${child.id}`"
                :title="child.text"
              />
            </OAnchorItem>
          </OAnchor>
        </aside>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.docs-page {
  position: relative;
  min-height: 100vh;
  padding-bottom: 64px;
  /* 不额外刷底色：与 body 底色（--color-bg）保持一致，避免页面盒子底边出现色差分界线 */
  background: transparent;
}

/* ===== 顶部纹理 ===== */
.hero-texture {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 450px;
  overflow: hidden;
  pointer-events: none;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.container-wide {
  position: relative;
  max-width: 1488px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ===== 页面标题（对齐参考站「使用指南」：48px / semibold） ===== */
.page-title {
  padding-top: 40px;
  margin: 0 0 40px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: var(--o-font_size-display2);
  line-height: var(--o-line_height-display2);
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

/* ===== 左目录 + 右正文 ===== */
.docs-layout {
  display: flex;
  align-items: flex-start;
  gap: 32px;
}

.docs-sidebar {
  position: sticky;
  /* 避开顶部 72px 吸顶导航，再留 24px 间距 */
  top: 96px;
  box-sizing: border-box;
  width: 280px;
  flex-shrink: 0;
  /* 无底色面板：去掉水平内边距，让「文档导航」与页面标题左对齐 */
  padding: 24px 0;
  background: transparent;
}

/* 面板标题：左「文档导航」与右「本内容」共用（对齐参考站：12px / 40% 黑） */
.panel-title {
  margin: 0 0 12px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: var(--o-font_size-tip2);
  line-height: var(--o_line_height-tip2);
  letter-spacing: 0px;
  /* info4 在浅色为 40% 黑、深色为 40% 白，随主题自动适配 */
  color: var(--o-color-info4);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 一级：可折叠分类行（对齐参考站：14px / semibold / 80% 黑 + 14px 箭头） */
.nav-group-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  box-sizing: border-box;
  width: 100%;
  padding: 6px 0;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: var(--o-font_size-tip1);
  line-height: var(--o_line_height-tip1);
  letter-spacing: 0px;
  color: var(--o-color-info2);
  transition: color 0.15s;

  @include hover {
    color: var(--o-color-info1);
  }
}

/* 折叠箭头：默认朝右，展开时转 90° 朝下 */
.nav-group-chevron {
  flex-shrink: 0;
  font-size: 14px;
  color: var(--o-color-info4);
  transition: transform 0.15s;

  &.is-expanded {
    transform: rotate(90deg);
  }
}

.nav-group-items {
  margin: 2px 0 0;
  padding: 0;
  list-style: none;

  > li + li {
    margin-top: 2px;
  }
}

/* 二级：文档链接（左侧 2px 指示条标记当前文档，未选中为透明占位不产生位移） */
.sidebar-link {
  display: block;
  box-sizing: border-box;
  padding: 6px 0 6px 20px;
  border-left: 2px solid transparent;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-tip1);
  line-height: var(--o_line_height-tip1);
  letter-spacing: 0px;
  color: var(--o-color-info3);
  text-decoration: none;
  transition: color 0.15s, border-color 0.15s;

  @include hover {
    color: var(--o-color-info1);
  }

  &.is-active {
    border-left-color: var(--o-color-info1);
    font-weight: var(--o-font_weight-medium);
    color: var(--o-color-info1);
  }
}

.docs-main {
  flex: 1;
  min-width: 0;
}

/* 右侧「本内容」：页内目录面板，随页面吸顶 */
.docs-toc {
  position: sticky;
  /* 与左侧导航同一吸顶基准（72px 吸顶导航 + 24px 间距） */
  top: 96px;
  box-sizing: border-box;
  width: 260px;
  flex-shrink: 0;
  /* 无底色面板：与左栏保持一致，去掉水平内边距 */
  padding: 24px 0;
  background: transparent;
}

/* OAnchor 自带圆点/竖线/高亮样式，仅收窄标题行距以贴合面板密度 */
.toc-anchor {
  --anchor-item-max-row: 1;
}

.docs-card {
  box-sizing: border-box;
  /* 正文区同样不带底色，整页共用页面背景 */
  background: transparent;
  padding: 48px;
}

.state-card {
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

/* Markdown 正文（.doc-body 系列样式）已收敛到 @/components/MarkdownRenderer.vue */

/* ===== 响应式 ===== */
/* 全站以 1488px 画布为基准（main.css 固定 min-width，移动端整页等比缩放），
   故不重排三栏结构；仅在窄窗口下隐去右栏「本内容」，优先保证正文阅读宽度 */
@media (max-width: 1200px) {
  .docs-toc {
    display: none;
  }

  .docs-sidebar {
    width: 240px;
  }
}
</style>