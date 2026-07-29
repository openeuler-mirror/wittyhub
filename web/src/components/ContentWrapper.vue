<script setup lang="ts">
/**
 * 内容区域容器组件
 * 统一 max-width、水平 padding 和垂直 padding
 */
import { isBoolean, isString, isUndefined } from '@opensig/opendesign'
import { computed } from 'vue'

interface ContentWrapperPropsT {
  verticalPadding?: boolean | string | Array<string>
}

const DEFAULT = Symbol('default')

const props = withDefaults(defineProps<ContentWrapperPropsT>(), {
  verticalPadding: undefined,
})

const paddingTop = computed(() => {
  if (!props.verticalPadding) return 0
  if (isBoolean(props.verticalPadding)) return DEFAULT
  if (isString(props.verticalPadding)) return props.verticalPadding
  return props.verticalPadding[0]
})

const paddingBottom = computed(() => {
  if (!props.verticalPadding) return 0
  if (isBoolean(props.verticalPadding)) return DEFAULT
  if (isString(props.verticalPadding)) return props.verticalPadding
  return !isUndefined(props.verticalPadding[1]) ? props.verticalPadding[1] : props.verticalPadding[0]
})
</script>

<template>
  <div
    class="content-wrapper"
    :style="{
      '--content-wrapper-vertical-paddingTop': paddingTop === DEFAULT ? undefined : paddingTop,
      '--content-wrapper-vertical-paddingBottom': paddingBottom === DEFAULT ? undefined : paddingBottom,
    }"
  >
    <slot></slot>
  </div>
</template>

<style lang="scss" scoped>
.content-wrapper {
  max-width: var(--layout-content-max-width, 1488px);
  padding-left: var(--layout-content-padding, 24px);
  padding-right: var(--layout-content-padding, 24px);
  margin: 0 auto;
  --content-wrapper-vertical-paddingTop: 0;
  --content-wrapper-vertical-paddingBottom: 0;
  padding-top: var(--content-wrapper-vertical-paddingTop);
  padding-bottom: var(--content-wrapper-vertical-paddingBottom);
}
</style>
