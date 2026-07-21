<script setup lang="ts">
import { ref } from 'vue'
import { useScreen } from '@/composables/useScreen'
import { useAppStore } from '@/stores/app'
import { OIcon } from '@opensig/opendesign'
import ContentWrapper from './ContentWrapper.vue'
import HeaderNav from './HeaderNav.vue'
import HeaderNavMoblie from './HeaderNavMoblie.vue'
import logoSrc from '@/assets/header/logo.svg'
import logoDarkSrc from '@/assets/header/logo_dark.svg'

const appStore = useAppStore()
const { lePadV } = useScreen()

const menuShow = ref(false)

const menuPanel = () => {
  setTimeout(() => {
    menuShow.value = !menuShow.value
    document.body.style.overflow = menuShow.value ? 'hidden' : ''
  }, 200)
}
</script>

<template>
  <header
    class="app-header"
    :class="{ dark: appStore.isDark }"
  >
    <ContentWrapper class="app-header-wrap">
      <!-- 移动端菜单图标 -->
      <div v-if="lePadV" class="menu-icon">
        <div class="icon" @click="menuPanel">
          <OIcon>
            <svg v-if="!menuShow" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
            <svg v-else width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </OIcon>
        </div>
      </div>

      <!-- Logo -->
      <a href="https://www.openeuler.openatom.cn/zh/" class="logo-link">
        <img
          class="logo"
          alt="openEuler logo"
          :src="appStore.isDark ? logoDarkSrc : logoSrc"
        />
      </a>
      <div class="logo-divider"></div>
      <a href="/" class="skillhub-title">SkillHub</a>

      <!-- 桌面端导航 -->
      <HeaderNav v-if="!lePadV" />

      <!-- 移动端导航 -->
      <HeaderNavMoblie
        v-if="lePadV"
        :menu-show="menuShow"
        @link-click="menuPanel"
      />
    </ContentWrapper>
  </header>
</template>

<style lang="scss" scoped>
.app-header {
  background-color: var(--o-color-fill2);
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  z-index: 98;
  box-shadow: var(--o-shadow-1);
  backdrop-filter: blur(5px);

  @include respond-to('>pad_v') {
    &.dark {
      &:after {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 1px;
        background-color: var(--o-color-control4);
      }
    }

    &:before {
      bottom: 0;
      box-shadow: var(--o-shadow-1);
      content: '';
      left: 0;
      pointer-events: none;
      position: absolute;
      right: 0;
      top: 0;
      z-index: 100;
    }
  }

  .app-header-wrap {
    display: flex;
    align-items: center;
    @include respond-to('>pad_v') {
      height: 80px;
    }
    @include respond-to('<=pad_v') {
      height: 48px;
      justify-content: space-between;
      position: relative;
    }
  }
}

.logo {
  cursor: pointer;
  flex-shrink: 0;

  @include respond-to('>pad_v') {
    height: 32px;
    width: 136px;

    @include respond-to('laptop') {
      margin-right: 0;
    }
    @include respond-to('pad_h') {
      margin-right: 0;
    }
  }

  @include respond-to('<=pad_v') {
    height: 24px;
    width: 136px;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    top: 12px;
  }
}

.logo-divider {
  width: 1px;
  height: 24px;
  background-color: var(--o-color-control4);
  margin: 0 16px;
  flex-shrink: 0;

  @include respond-to('<=pad_v') {
    display: none;
  }
}

.skillhub-title {
  font-weight: 700;
  font-size: 18px;
  line-height: 24px;
  color: var(--o-color-info1);
  text-decoration: none;
  flex-shrink: 0;
  margin-right: var(--o-gap-7);

  @include respond-to('laptop') {
    margin-right: 28px;
  }
  @include respond-to('pad_h') {
    margin-right: var(--o-gap-2);
  }
  @include respond-to('<=pad_v') {
    display: none;
  }

  @include hover {
    color: var(--o-color-primary1);
  }
}

.menu-icon {
  flex: 1;
  display: block;
  .icon {
    font-size: var(--o-icon_size-m);
    color: var(--o-color-info1);
    height: 24px;
    cursor: pointer;
  }
}
</style>
