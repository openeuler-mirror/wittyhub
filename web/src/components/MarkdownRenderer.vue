<script lang="ts">
/**
 * 章节大纲项：h2 为一级、h3 挂在其 children 下（文档页左侧目录/页内目录使用）
 */
export interface OutlineItem {
  id: string
  text: string
  children: Array<{ id: string; text: string }>
}

/** 目录项为纯文本，需还原 HTML 实体（如 &quot;） */
function decodeEntities(text: string): string {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
}

/** 为正文 h2/h3 注入锚点 id（doc-section-N / N-M），并产出章节大纲 */
export function parseOutline(html: string): { html: string; outline: OutlineItem[] } {
  const outline: OutlineItem[] = []
  let h2Count = 0
  let h3Count = 0
  const result = html.replace(/<(h2|h3)>([\s\S]*?)<\/\1>/g, (_match, tag: string, inner: string) => {
    const text = decodeEntities(inner.replace(/<[^>]+>/g, '').trim())
    if (tag === 'h2') {
      h2Count += 1
      h3Count = 0
      const id = `doc-section-${h2Count}`
      outline.push({ id, text, children: [] })
      return `<h2 id="${id}">${inner}</h2>`
    }
    // h3 挂到最近的 h2 下；若 h2 之前出现 h3，则作为一级项兜底
    h3Count += 1
    const id = `doc-section-${h2Count}-${h3Count}`
    const parent = outline[outline.length - 1]
    if (parent) parent.children.push({ id, text })
    else outline.push({ id, text, children: [] })
    return `<h3 id="${id}">${inner}</h3>`
  })
  return { html: result, outline }
}

/** 由 Markdown 原文解析章节大纲（文档页左侧目录使用，锚点 id 规则与正文渲染一致） */
export function parseDocOutline(source: string): OutlineItem[] {
  return parseOutline(marked.parse(source) as string).outline
}
</script>

<script setup lang="ts">
/**
 * Markdown 正文渲染组件（站点文档页正文使用）。
 *
 * 排版规格与技能详情页「使用描述」块保持一致（同一套字号/行高/标题/列表/表格/代码块样式，
 * 代码块同样使用 shiki 双主题高亮并带复制按钮），保证两处正文观感一致。
 *
 * 同时承接文档页专有逻辑：
 * - marked 解析 + 相对 md 链接改写为站内文档路由，保证文档互链不出站；
 * - 文档中的安全等级 emoji 改写为受控色点（各环境 emoji 字体支持不一致）；
 * - h2/h3 注入锚点 id（保留 scroll-margin，避开吸顶导航）并通过 `v-model:outline`
 *   回传章节大纲，供页内目录联动。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import { createHighlighter, type Highlighter } from 'shiki'
import { useRouter } from 'vue-router'
import copySvg from '@/assets/icons/copy.svg?raw'
import checkSvg from '@/assets/icons/check.svg?raw'

const props = defineProps<{
  /** Markdown 原文 */
  source: string
  /**
   * 排版变体：
   * - default：与技能详情页「使用描述」块一致（默认）
   * - docs：文档页（使用指南）版式，对齐设计稿「使用指南示例」的 28/40 标题、20/28 二级标题等规格
   */
  variant?: 'default' | 'docs'
}>()

const emit = defineEmits<{
  /** 解析结果变化时回传章节大纲 */
  'update:outline': [outline: OutlineItem[]]
}>()

const router = useRouter()

/**
 * 正文内链拦截：Markdown 里的相对链接被改写为 `/docs/xxx` 的原生 <a>，
 * 直接点击会触发浏览器整页导航（整页刷新）。此处改为交给 vue-router 处理，
 * 与文档页左栏目保持一致的客户端跳转；外链/新标签打开等保持默认行为。
 */
function handleContentClick(e: MouseEvent) {
  // 代码块复制按钮由同一容器承接
  handleCodeClick(e)

  const target = e.target as HTMLElement | null
  const anchor = target?.closest('a') as HTMLAnchorElement | null
  if (!anchor) return
  // 仅拦截站内文档链接，外链（http/https/mailto 等）交给浏览器
  const href = anchor.getAttribute('href') || ''
  if (!href.startsWith('/docs/')) return
  // Cmd/Ctrl/Shift/Alt 或中键等保留默认行为（新标签打开）
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
  e.preventDefault()
  router.push(href)
}

/** 安全等级 emoji → 色点修饰类（配色与详情页/报告页保持一致） */
const LEVEL_DOTS: Record<string, string> = {
  '🟢': 'safe',
  '🔵': 'low',
  '🟠': 'medium',
  '🔴': 'high',
  '⚪': 'unknown',
}

// ===== Shiki 代码高亮（主题/语言与详情页「使用描述」保持一致） =====
let highlighter: Highlighter | null = null
const highlighterReady = ref(false)

async function initHighlighter() {
  highlighter = await createHighlighter({
    themes: ['github-light', 'github-dark'],
    langs: ['bash', 'shell', 'javascript', 'typescript', 'python', 'json', 'yaml', 'markdown', 'html', 'css', 'vue', 'sql', 'go', 'java', 'rust', 'xml', 'diff']
  })
  highlighterReady.value = true
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/** 代码块渲染：shiki 高亮 + 复制按钮（高亮器就绪前先输出纯文本，就绪后自动重渲染）
 *  未标注语言的代码块按纯文本高亮，保证代码块外观与详情页「使用描述」一致 */
const renderer = new marked.Renderer()
renderer.code = (code: string, lang: string | undefined) => {
  let highlighted: string
  if (highlighterReady.value && highlighter) {
    try {
      highlighted = highlighter.codeToHtml(code, {
        lang: lang || 'text',
        themes: { light: 'github-light', dark: 'github-dark' }
      })
    } catch {
      highlighted = `<pre><code>${escapeHtml(code)}</code></pre>`
    }
  } else {
    highlighted = `<pre><code>${escapeHtml(code)}</code></pre>`
  }
  return `<div class="code-block-wrap">
  <button class="code-copy-btn" data-code="${code.replace(/"/g, '&quot;')}" aria-label="复制代码">${copySvg}</button>
  ${highlighted}
</div>\n`
}

/** 解析 Markdown：一次解析同时产出正文 HTML 与章节大纲（h2/h3 注入锚点 id） */
const parsed = computed<{ html: string; outline: OutlineItem[] }>(() => {
  if (!props.source) return { html: '', outline: [] }

  // 相对 md 链接改写为站内文档路由
  let html = marked.parse(props.source, { renderer }) as string
  html = html.replace(/href="\.?\/?([\w-]+)\.md"/g, 'href="/docs/$1"')

  // 安全等级色点：文档用 emoji 表示等级，各环境 emoji 字体支持不一致，
  // 统一改写为受控色点，保证颜色稳定显示（配色与详情页/报告页一致）
  html = html.replace(/(🟢|🔵|🟠|🔴|⚪)\uFE0F?/gu, (_match, emoji: string) => {
    return `<span class="level-dot level-dot--${LEVEL_DOTS[emoji]}"></span>`
  })

  return parseOutline(html)
})

/** 大纲同步给父级：首屏渲染与切换文档时都会触发 */
watch(parsed, (value) => emit('update:outline', value.outline), { immediate: true })

/** 代码复制：文档页没有全局 Toast，复制成功后用按钮自身状态（与详情页同一套 .is-copied 样式）反馈 */
async function handleCodeClick(e: MouseEvent) {
  const btn = (e.target as HTMLElement).closest('.code-copy-btn') as HTMLElement | null
  if (!btn || btn.classList.contains('is-copied')) return
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
    btn.classList.add('is-copied')
    btn.innerHTML = checkSvg
    window.setTimeout(() => {
      btn.classList.remove('is-copied')
      btn.innerHTML = copySvg
    }, 2000)
  } catch (err) {
    console.error('复制代码失败:', err)
  }
}

onMounted(initHighlighter)
</script>

<template>
  <div
    class="markdown-body"
    :class="{ 'markdown-body--docs': variant === 'docs' }"
    v-html="parsed.html"
    @click="handleContentClick"
  ></div>
</template>

<style lang="scss" scoped>
/* 排版规格取自技能详情页「使用描述」块（.markdown-body），保持两处正文观感一致 */
.markdown-body {
  color: var(--o-color-info1);
  font-size: 15px;
  line-height: 1.8;

  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    margin-top: 24px;
    margin-bottom: 24px;
    color: var(--o-color-info1);
    font-weight: 600;
  }

  :deep(h1) {
    margin-top: 0;
    margin-bottom: 12px;
    color: var(--o-color-info1);
    font-family: var(--o-font_family);
    font-weight: var(--o-font_weight-semibold);
    font-size: var(--o-font_size-h1);
    line-height: var(--o-line_height-h1);
    letter-spacing: 0px;
    text-align: left;
  }

  /* 文档页专有：锚点跳转时避开顶部 72px 吸顶导航（右侧「本内容」目录依赖） */
  :deep(h2),
  :deep(h3) {
    scroll-margin-top: 96px;
  }

  :deep(h2) {
    margin-bottom: 8px;
    font-size: 24px;
  }
  :deep(h3) { font-size: 20px; }
  :deep(h4) { font-size: 15px; }
  :deep(h5) { font-size: 14px; }
  :deep(h6) { font-size: 13px; }

  :deep(p) {
    margin-bottom: 8px;
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
    margin-bottom: 8px;
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
    background: var(--o-color-control2-light);
    border-radius: 4px;
    padding: 16px;
    overflow-x: auto;
    margin-bottom: 16px;
    color: var(--o-color-info1);
    font-family: HarmonyHeiTi;
    font-weight: regular;
    font-size: 14px;
    line-height: 22px;
    letter-spacing: 0px;
    text-align: left;

    &::-webkit-scrollbar {
      height: 4px;
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
      color: inherit;
      font-size: 14px;
    }
    font-size: 14px;
  }

  /* ===== Shiki 双主题：浅色默认，深色由 --shiki-dark ===== */
  :deep(.shiki) {
    background-color: #F3F3F5 !important;
    border-radius: 4px;
    color: var(--shiki-light) !important;
  }

  :deep(.shiki span) {
    color: var(--shiki-light);
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
      border: none;
      text-align: left;
      font-size: 14px;
    }

    th {
      border-radius: 4px 4px 0px 0px;
      background: #FFFFFF;
      border: none;
      border-bottom: 1px solid #002FA7;
      font-weight: 600;
      color: var(--o-color-info2);
    }

    tbody tr {
      background: #FFFFFF02;

      &:nth-child(even) {
        background: #EBF1FA66;
      }

      td {
        border: none;
        color: var(--o-color-info2);
      }
    }
  }

  :deep(hr) {
    display: none;
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

  /* 安全等级色点（由文档中的等级 emoji 改写而来） */
  :deep(.level-dot) {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 6px;
    border-radius: 50%;
    vertical-align: middle;
  }

  :deep(.level-dot--safe) {
    background: var(--o-color-success1);
  }

  /* 低风险蓝：设计稿定值，与详情页/报告页一致 */
  :deep(.level-dot--low) {
    background: #497af8;
  }

  :deep(.level-dot--medium) {
    background: var(--o-color-warning1);
  }

  :deep(.level-dot--high) {
    background: var(--o-color-danger1);
  }

  :deep(.level-dot--unknown) {
    background: var(--o-color-info3);
  }
}

/* ===== 文档页变体（docs）：版式对齐设计稿「使用指南示例」 =====
   与技能详情页「使用描述」的差异：标题更紧凑（28/40、20/28、18/26）、正文行高 24、
   引用块为浅蓝色块（圆角 4、内边距 24）、表格固定 960px（首列 401px，其余列均分）、
   无序列表为 6px 圆点 + 文本缩进 38px */
.markdown-body.markdown-body--docs {
  :deep(h1) {
    margin: 0 0 32px;
    /* 设计稿定值：28/40 */
    font-size: 28px;
    line-height: 40px;
    font-weight: var(--o-font_weight-medium);
  }

  :deep(h2) {
    margin: 32px 0 12px;
    font-size: var(--o-font_size-h4);
    line-height: var(--o-line_height-h4);
    font-weight: var(--o-font_weight-medium);
  }

  :deep(h3) {
    margin: 12px 0;
    font-size: var(--o-font_size-text2);
    line-height: var(--o-line_height-text2);
    font-weight: var(--o-font_weight-medium);
  }

  :deep(h4),
  :deep(h5),
  :deep(h6) {
    margin: 12px 0;
    font-size: var(--o-font_size-text1);
    line-height: var(--o-line_height-text1);
    font-weight: var(--o-font_weight-medium);
  }

  :deep(p) {
    margin: 0 0 8px;
    font-size: var(--o-font_size-text1);
    line-height: var(--o-line_height-text1);
  }

  /* 圆点距正文左边缘 24px、文本缩进 38px（设计稿） */
  :deep(ul) {
    margin: 0 0 8px;
    padding-left: 38px;
    list-style: none;
  }

  :deep(ul > li) {
    position: relative;
    margin-bottom: 0;
    font-size: var(--o-font_size-text1);
    line-height: var(--o-line_height-text1);

    &::before {
      content: '';
      position: absolute;
      left: -14px;
      top: 9px;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--o-color-info1);
    }
  }

  :deep(ol) {
    margin: 0 0 8px;
    padding-left: 38px;
  }

  :deep(ol > li) {
    margin-bottom: 0;
    font-size: var(--o-font_size-text1);
    line-height: var(--o-line_height-text1);
  }

  /* 引用块：浅蓝色块 + 圆角 4 + 内边距 24，无左侧竖线（设计稿） */
  :deep(blockquote) {
    margin: 12px 0;
    padding: 24px;
    border-left: none;
    border-radius: 4px;
    background: var(--o-color-control2-light);
    color: var(--o-color-info1);

    p {
      margin: 0;
    }
  }

  /* 表格：固定 960px 宽，首列 401px，其余列均分（设计稿） */
  :deep(table) {
    width: 960px;
    max-width: 100%;
    margin: 12px 0;
  }

  :deep(th),
  :deep(td) {
    padding: 8px 24px;
    background: transparent;
    font-size: var(--o-font_size-tip1);
    line-height: var(--o-line_height-tip1);
    color: var(--o-color-info1);
  }

  /* 首列列宽由首行单元格决定（设计稿：401px） */
  :deep(th:first-child),
  :deep(td:first-child) {
    width: 401px;
  }

  :deep(th) {
    border-radius: 0;
    border-bottom: 1px solid var(--o-color-primary1);
    font-weight: var(--o-font_weight-semibold);
    color: var(--o-color-info2);
  }

  :deep(tbody tr) {
    background: transparent;

    /* 设计稿：#EBF1FA 40% */
    &:nth-child(even) {
      background: rgba(235, 241, 250, 0.4);
    }
  }
}

/* ===== Shiki 深色模式覆盖 ===== */
[data-o-theme='e.dark'] .markdown-body {
  :deep(.shiki),
  :deep(.shiki span) {
    background-color: var(--o-color-control2-light) !important;
    color: var(--shiki-dark) !important;
    font-style: var(--shiki-dark-font-style) !important;
    font-weight: var(--shiki-dark-font-weight) !important;
    text-decoration: var(--shiki-dark-text-decoration) !important;
  }

  :deep(table th) {
    background: var(--o-color-control2-light);
    border-bottom-color: var(--o-color-primary1);
  }

  :deep(table tbody tr) {
    background: transparent;
  }

  :deep(table tbody tr:nth-child(even)) {
    background: rgba(255, 255, 255, 0.04);
  }
}
</style>