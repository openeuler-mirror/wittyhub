<script setup lang="ts">
import { ref } from 'vue'
import copySvg from '@/assets/icons/copy.svg?raw'

const props = withDefaults(
  defineProps<{
    /** 提示词文本（复制内容） */
    prompt: string
    /** 卡片标题 */
    label?: string
    /** 标题下方说明文字 */
    hint?: string
    /** 内容对齐方式 */
    align?: 'left' | 'center'
    /** 复制按钮文案；不传则显示图标按钮 */
    buttonText?: string
    /** 卡片外观：card 带背景，plain 透明 */
    variant?: 'card' | 'plain'
    /** 提示词单行显示（不换行，超出省略） */
    nowrap?: boolean
  }>(),
  {
    label: '',
    hint: '',
    align: 'left',
    buttonText: '',
    variant: 'card',
    nowrap: false
  }
)

const copied = ref(false)

async function copyPrompt() {
  const text = props.prompt
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // HTTP 等无剪贴板 API 场景的兜底
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    console.error('复制失败:', e)
  }
}
</script>

<template>
  <div
    class="prompt-card"
    :class="{
      'is-center': props.align === 'center',
      'is-plain': props.variant === 'plain',
      'is-nowrap': props.nowrap
    }"
  >
    <h3 v-if="label" class="prompt-label">{{ label }}</h3>
    <p v-if="hint" class="prompt-hint">{{ hint }}</p>
    <div class="prompt-input-group">
      <code class="prompt-text">{{ prompt }}</code>
      <button
        class="prompt-copy-btn"
        :class="{ 'is-copied': copied, 'is-text': !!props.buttonText }"
        :aria-label="copied ? '已复制' : props.buttonText || '复制'"
        @click="copyPrompt"
      >
        <template v-if="props.buttonText">
          <span v-if="!copied" class="btn-text">
            <span class="btn-icon copy-icon" v-html="copySvg"></span>
            {{ props.buttonText }}
          </span>
          <span v-else class="btn-text copied-text">
            <span class="btn-icon copied-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M5 13l4 4L19 7"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
            已复制
          </span>
        </template>
        <template v-else>
          <span v-if="!copied" class="btn-icon" v-html="copySvg"></span>
          <span v-else class="btn-icon copied-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" fill="currentColor" />
              <path
                d="M8 12l3 3 5-5"
                stroke="#fff"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
        </template>
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.prompt-card {
  background: var(--o-color-fill2);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prompt-label {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: var(--o-font_size-h3);
  line-height: var(--o-line_height-h3);
  letter-spacing: 0;
  text-align: left;
  color: var(--o-color-info1);
}

.prompt-hint {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-tip1);
  line-height: var(--o-line_height-tip1);
  letter-spacing: 0;
  text-align: left;
  color: var(--o-color-info3);
}

.prompt-input-group {
  display: flex;
  align-items: center;
  background: var(--o-color-fill3);
  border-radius: 6px;
}

/* 居中展示：标题/说明/提示词文本全部居中 */
.is-center .prompt-label,
.is-center .prompt-hint,
.is-center .prompt-text {
  text-align: center;
}

/* plain 外观：去掉卡片与输入区背景，仅保留细边框 */
.prompt-card.is-plain {
  background: transparent;
  padding: 0;
}

.is-plain .prompt-input-group {
  background: transparent;
  border: 1px solid var(--o-color-control4);
}

/* 单行展示：不换行、不截断，完整显示 */
.is-nowrap .prompt-input-group {
  align-items: center;
}

.is-nowrap .prompt-text {
  white-space: nowrap;
  overflow: visible;
  word-break: normal;
}

.prompt-text {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  font-family: var(--o-font_family-code);
  font-size: 13px;
  line-height: 20px;
  color: var(--o-color-info1);
  word-break: normal;
  overflow-wrap: anywhere;
  white-space: normal;
}

.prompt-copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin: 10px 12px 10px 0;
  border: none;
  background: transparent;
  color: var(--o-color-info3);
  cursor: pointer;
  transition: color 0.2s;
  flex-shrink: 0;

  @include hover {
    color: var(--o-color-primary1);
  }

  &.is-copied {
    color: var(--o-color-success1);
    cursor: default;
  }
}

/* 文字按钮形态：主色填充 + 白字 */
.prompt-copy-btn.is-text {
  width: auto;
  height: 32px;
  margin: 8px 8px 8px 0;
  padding: 0 12px;
  border-radius: 4px;
  background: var(--o-color-primary1);
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: var(--o-r-font_size-tip1);
  line-height: var(--o-r-line_height-tip1);
  color: #fff;
  white-space: nowrap;

  @include hover {
    background: color-mix(in srgb, var(--o-color-primary1) 85%, #000);
    color: #fff;
  }

  &.is-copied {
    background: var(--o-color-success1);
    color: #fff;
  }
}

.btn-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;

  .btn-icon {
    width: 14px;
    height: 14px;

    :deep(svg) {
      width: 14px;
      height: 14px;
    }
  }
}

.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;

  :deep(svg) {
    width: 16px;
    height: 16px;
    display: block;
  }
}

.copied-icon {
  width: 16px;
  height: 16px;

  :deep(svg) {
    width: 16px;
    height: 16px;
  }
}
</style>