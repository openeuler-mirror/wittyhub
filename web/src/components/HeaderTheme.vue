<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { OIcon } from '@opensig/opendesign'
import moonIcon from '@/assets/icons/moon.svg?raw'
import sunIcon from '@/assets/icons/sun.svg?raw'

const appStore = useAppStore()
</script>

<template>
  <div class="theme-wrapper">
    <div class="theme-box-pc" @click="appStore.toggleTheme()">
      <OIcon class="icon">
        <span v-if="!appStore.isDark" class="w-6 h-6 icon-svg" v-html="moonIcon"></span>
        <span v-else class="w-6 h-6 icon-svg" v-html="sunIcon"></span>
      </OIcon>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.theme-wrapper {
  display: flex;
  align-items: center;
}

.icon-svg {
  display: inline-flex;
  align-items: center;
  justify-content: center;

  :deep(svg) {
    width: 100%;
    height: 100%;
  }
}

.theme-box-pc {
  cursor: pointer;
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 8px;

  .icon {
    font-size: 20px;
    color: var(--o-color-info1, #1F2329);
    display: flex;
    align-items: center;
    transition: color 0.15s;

    &:hover {
      color: var(--o-color-primary1, #002FA7);
    }
  }
}
</style>
