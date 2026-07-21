<script setup lang="ts">
import { useScreen } from '@/composables/useScreen'
import { useAppStore } from '@/stores/app'
import { OIcon } from '@opensig/opendesign'

const appStore = useAppStore()
const { lePadV } = useScreen()
</script>

<template>
  <div class="theme-wrapper">
    <div v-if="lePadV" class="theme-box-mobile">
      <button class="theme-btn-mobile" @click="appStore.toggleTheme()">
        <svg v-if="appStore.isDark" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.653l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
        </svg>
      </button>
    </div>
    <div v-else class="theme-box-pc" @click="appStore.toggleTheme()">
      <OIcon class="icon">
        <svg v-if="!appStore.isDark" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.653l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
        </svg>
      </OIcon>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.theme-wrapper {
  display: flex;
  align-items: center;
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

  @include respond-to('<=pad_v') {
    display: none;
  }
}

.theme-box-mobile {
  display: none;

  @include respond-to('<=pad_v') {
    display: flex;
    align-items: center;
    justify-content: center;

    .theme-btn-mobile {
      width: 99px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      color: var(--o-color-info1, #1F2329);
      cursor: pointer;
      @include hover {
        color: var(--o-color-primary1, #002FA7);
      }
    }
  }
}
</style>
