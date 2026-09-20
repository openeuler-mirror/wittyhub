<script setup lang="ts">
/**
 * 站内文档页：左侧文档目录（三篇文档 + 当前文档标题大纲），右侧渲染正文。
 *
 * 文档源文件位于仓库 `docs/`，发布时同步一份到 `web/public/docs/`（web 镜像只打包
 * web/ 目录），页面按路由参数 `:doc` 取 `/docs/{doc}.md` 渲染，文档内的相对 md
 * 链接改写为站内路由，保证「查看详情」类入口不出站。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { OBreadcrumb, OBreadcrumbItem, OIconFile, OLoading } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'

const route = useRoute()
const appStore = useAppStore()

/** 文档目录（与 web/public/docs 下已同步的文档一致，顺序即侧栏展示顺序） */
const DOC_NAMES = ['skillhub-introduction', 'skillhub-publish-and-manage', 'skillhub-security-audit']

const content = ref('')
const loading = ref(true)
const error = ref('')
const docList = ref(DOC_NAMES.map((name) => ({ name, title: name })))

/** 路由参数只允许字母/数字/连字符，避免路径穿越 */
const docName = computed(() => String(route.params.doc || '').replace(/[^a-zA-Z0-9-]/g, ''))

/** 文档标题：取 Markdown 首个一级标题 */
const title = computed(() => {
  const match = content.value.match(/^#\s+(.+)$/m)
  return match ? match[1].trim() : '文档'
})

/** 目录项为纯文本，需还原 HTML 实体（如 &quot;） */
function decodeEntities(text: string): string {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
}

/** 正文渲染（含文档 H1，整篇作为一个完整文档展示）+ 标题大纲（给 h2 加锚点 id） */
const parsed = computed<{ html: string; outline: Array<{ id: string; text: string }> }>(() => {
  if (!content.value) return { html: '', outline: [] }

  // 相对 md 链接改写为站内文档路由
  let html = marked.parse(content.value) as string
  html = html.replace(/href="\.?\/?([\w-]+)\.md"/g, 'href="/docs/$1"')

  const outline: Array<{ id: string; text: string }> = []
  html = html.replace(/<h2>([\s\S]*?)<\/h2>/g, (_match, inner: string) => {
    const id = `doc-section-${outline.length + 1}`
    outline.push({ id, text: decodeEntities(inner.replace(/<[^>]+>/g, '').trim()) })
    return `<h2 id="${id}">${inner}</h2>`
  })
  return { html, outline }
})

const rendered = computed(() => parsed.value.html)
const outline = computed(() => parsed.value.outline)

/** 目录锚点滚动（不走上游路由，避免 hash 导航把页面滚回顶部） */
function scrollToAnchor(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** 目录列表：读取每篇文档的 H1 作为标题 */
async function loadDocList() {
  docList.value = await Promise.all(
    DOC_NAMES.map(async (name) => {
      try {
        const response = await fetch(`/docs/${name}.md`)
        if (!response.ok) throw new Error(String(response.status))
        const match = (await response.text()).match(/^#\s+(.+)$/m)
        return { name, title: match ? match[1].trim() : name }
      } catch {
        return { name, title: name }
      }
    })
  )
}

async function loadDoc() {
  loading.value = true
  error.value = ''
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
  loadDocList()
  loadDoc()
})
watch(() => route.params.doc, loadDoc)
</script>

<template>
  <div class="docs-page">
    <!-- 顶部纹理（与详情页/报告页同一张 hero 底纹） -->
    <div class="hero-texture">
      <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" />
    </div>

    <div class="container-wide">
      <div class="breadcrumb-wrap">
        <OBreadcrumb
          style="
            --breadcrumb-text-size: 14px;
            --breadcrumb-text-height: 22px;
            --breadcrumb-separator-size: 24px;
            --breadcrumb-gap: 4px;
          "
        >
          <OBreadcrumbItem to="/">SkillHub</OBreadcrumbItem>
          <OBreadcrumbItem>文档</OBreadcrumbItem>
          <OBreadcrumbItem>{{ loading ? '加载中' : title }}</OBreadcrumbItem>
        </OBreadcrumb>
      </div>

      <div class="docs-layout">
        <!-- ========== 左：文档目录 ========== -->
        <aside class="docs-sidebar">
          <p class="sidebar-title">目录</p>
          <nav class="sidebar-nav">
            <div v-for="doc in docList" :key="doc.name" class="sidebar-group">
              <router-link
                class="sidebar-link"
                :class="{ 'is-active': doc.name === docName }"
                :to="`/docs/${doc.name}`"
              >
                <OIconFile class="sidebar-link-icon" />
                <span class="sidebar-link-text">{{ doc.title }}</span>
              </router-link>
              <!-- 当前文档的章节大纲 -->
              <div v-if="doc.name === docName && outline.length" class="sidebar-outline">
                <a
                  v-for="section in outline"
                  :key="section.id"
                  class="outline-link"
                  href="javascript:void(0)"
                  @click="scrollToAnchor(section.id)"
                >
                  {{ section.text }}
                </a>
              </div>
            </div>
          </nav>
        </aside>

        <!-- ========== 右：正文（整篇文档含标题一起渲染） ========== -->
        <div class="docs-main">
          <div v-if="loading" class="docs-card state-card">
            <OLoading v-model:visible="loading" size="medium" />
          </div>

          <div v-else-if="error" class="docs-card state-card">
            <p class="error-text">{{ error }}</p>
            <router-link class="back-link" to="/">返回首页</router-link>
          </div>

          <div v-else class="docs-card">
            <div class="doc-body" v-html="rendered"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.docs-page {
  position: relative;
  min-height: 100vh;
  padding-bottom: 64px;
  background: var(--o-color-fill1);
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
}

/* ===== 面包屑（与详情页/报告页一致） ===== */
.breadcrumb-wrap {
  padding-top: 40px;
  margin-bottom: 40px;

  --breadcrumb-color: #00000099;

  :deep(.o-breadcrumb-item-label) {
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    letter-spacing: 0px;
    color: var(--breadcrumb-color);
  }

  :deep(.o-breadcrumb-item:last-child .o-breadcrumb-item-label) {
    color: var(--o-color-primary1);
    font-weight: var(--o-font_weight-semibold);
  }

  :deep(.o-icon-chevron-right) {
    color: var(--breadcrumb-color);
  }
}

.dark .breadcrumb-wrap {
  --breadcrumb-color: rgba(255, 255, 255, 0.6);
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
  padding: 24px 16px;
  background: var(--o-color-fill2);
  border-radius: 4px;
}

.sidebar-title {
  margin: 0 0 12px;
  padding: 0 12px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight_medium);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 一级：文档章节 —— 卡片式导航项（文档图标 + 左侧指示条 + 悬停底色） */
.sidebar-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  box-sizing: border-box;
  padding: 10px 12px 10px 14px;
  border-radius: 4px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
  text-decoration: none;
  transition: color 0.2s, background-color 0.2s;

  /* 左侧指示条：标记当前章节（默认透明占位，选中时不产生位移） */
  &::before {
    content: '';
    position: absolute;
    left: 4px;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 16px;
    border-radius: 2px;
    background: transparent;
    transition: background-color 0.2s;
  }

  .sidebar-link-icon {
    flex-shrink: 0;
    font-size: 16px;
    color: var(--o-color-info3);
    transition: color 0.2s;
  }

  .sidebar-link-text {
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  @include hover {
    background: var(--o-color-fill3);
    color: var(--o-color-primary1);

    &::before {
      background: var(--o-color-control5);
    }

    .sidebar-link-icon {
      color: var(--o-color-primary1);
    }
  }

  &.is-active {
    background: var(--o-color-control2-light);
    color: var(--o-color-primary1);
    font-weight: var(--o-font_weight-semibold);

    &::before {
      background: var(--o-color-primary1);
    }

    .sidebar-link-icon {
      color: var(--o-color-primary1);
    }
  }
}

/* 当前文档的章节大纲 */
.sidebar-outline {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 4px 0 8px;
  padding-left: 14px;
  border-left: 1px solid var(--o-color-control4);
}

/* 二级：页内大纲 —— 纯文本子项（圆点 + 更小字号/行高 + 更浅文字），与一级章节项区分 */
.outline-link {
  position: relative;
  display: block;
  padding: 5px 8px 5px 12px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 13px;
  line-height: 20px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
  text-decoration: none;
  transition: color 0.2s;

  /* 前导圆点：二级子项标记，不与一级的文档图标/指示条混淆 */
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--o-color-control4);
    transition: background-color 0.2s;
  }

  /* 悬停仅加深文字色：不加底色、不切品牌色，与一级的交互反馈明显不同 */
  @include hover {
    color: var(--o-color-info1);

    &::before {
      background: var(--o-color-primary1);
    }
  }
}

.docs-main {
  flex: 1;
  min-width: 0;
}

.docs-card {
  box-sizing: border-box;
  background: var(--o-color-fill2);
  border-radius: 4px;
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

/* ===== Markdown 正文 ===== */
.doc-body {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 26px;
  letter-spacing: 0px;
  color: var(--o-color-info2);

  /* 文档标题（Markdown H1，与正文同属一篇文档） */
  :deep(h1) {
    margin: 0 0 24px;
    font-weight: var(--o-font_weight-semibold);
    font-size: 40px;
    line-height: 56px;
    color: var(--o-color-info1);
  }

  :deep(h2) {
    margin: 32px 0 16px;
    font-weight: var(--o-font_weight-semibold);
    font-size: 24px;
    line-height: 32px;
    color: var(--o-color-info1);
    /* 锚点跳转时避开顶部 72px 吸顶导航，再留 24px 呼吸空间 */
    scroll-margin-top: 96px;
  }

  :deep(h3) {
    margin: 24px 0 12px;
    font-weight: var(--o-font_weight-semibold);
    font-size: 20px;
    line-height: 28px;
    color: var(--o-color-info1);
  }

  :deep(p) {
    margin: 0 0 16px;
  }

  :deep(ul),
  :deep(ol) {
    margin: 0 0 16px;
    padding-left: 24px;
  }

  :deep(li) {
    margin-bottom: 8px;
  }

  :deep(a) {
    color: var(--o-color-link1);

    &:hover {
      color: var(--o-color-link2);
    }
  }

  :deep(strong) {
    font-weight: var(--o-font_weight_semibold);
    color: var(--o-color-info1);
  }

  :deep(code) {
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--o-color-control2-light);
    font-family: var(--o-font_family-code);
    font-size: 14px;
    color: var(--o-color-info1);
  }

  :deep(blockquote) {
    margin: 0 0 16px;
    padding-left: 16px;
    border-left: 3px solid var(--o-color-primary1);
    color: var(--o-color-info3);
  }

  :deep(table) {
    width: 100%;
    margin: 0 0 16px;
    border-collapse: collapse;
    font-size: 14px;
    line-height: 22px;
  }

  :deep(th),
  :deep(td) {
    padding: 10px 12px;
    text-align: left;
    color: var(--o-color-info1);
    border-bottom: 1px solid var(--o-color-control4);
  }

  :deep(th) {
    font-weight: var(--o-font_weight_semibold);
    background: var(--o-color-control2-light);
  }

  :deep(hr) {
    height: 1px;
    margin: 32px 0 24px;
    border: none;
    background: var(--o-color-control4);
  }

  > :deep(:first-child) {
    margin-top: 0;
  }
}
</style>