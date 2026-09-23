<script setup lang="ts">
import { useRoute } from 'vue-router'
import HeaderTheme from './HeaderTheme.vue'
import HeaderLogin from './HeaderLogin.vue'

const route = useRoute()

interface NavItem {
  label: string
  to?: string
  href?: string
  // match path prefixes (route.path starts with any of these)
  match?: string[]
}

const navItems: NavItem[] = [
  { label: 'Skills', to: '/', match: ['/', '/skills'] },
  { label: '贡献', to: '/contributors', match: ['/contributors'] },
  {
    label: '文档',
    to: '/docs/skillhub-introduction',
    match: ['/docs'],
  },
]

function isActive(item: NavItem): boolean {
  if (item.to && route.path === item.to) return true
  if (item.match) {
    return item.match.some(p => route.path === p || route.path.startsWith(p + '/'))
  }
  return false
}
</script>

<template>
  <div class="header-nav">
    <!-- 主导航 tabs -->
    <nav class="nav-tabs" aria-label="主导航">
      <template v-for="item in navItems" :key="item.label">
        <a
          v-if="item.to"
          :href="item.to"
          :class="['nav-tab', { active: isActive(item) }]"
          @click.prevent
        >
          <router-link :to="item.to" class="nav-tab-link">{{ item.label }}</router-link>
        </a>
        <a
          v-else-if="item.href"
          :href="item.href"
          target="_blank"
          rel="noopener noreferrer"
          class="nav-tab"
        >
          {{ item.label }}
        </a>
      </template>
    </nav>

    <div class="header-tool">
      <HeaderTheme />
      <HeaderLogin />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.header-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  height: 100%;
  overflow: hidden;
}

.nav-tabs {
  display: flex;
  align-items: stretch;
  height: 100%;
  gap: 0;
}

.nav-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 0 20px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  color: var(--o-color-info1);
  text-decoration: none;
  transition: color 0.15s;
  cursor: pointer;
  white-space: nowrap;

  &:hover {
    color: var(--o-color-primary1);
  }

  &.active {
    color: var(--o-color-primary1);
    font-weight: var(--o-font_weight-medium);

    /* 下划线 1px 高、与文字同宽（不含左右 padding）、primary1 */
    &::after {
      content: '';
      position: absolute;
      left: 20px;
      right: 20px;
      bottom: 0;
      height: 1px;
      background: var(--o-color-primary1);
    }
  }
}

.nav-tab-link {
  color: inherit;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.header-tool {
  display: flex;
  align-items: center;
  height: 100%;
  margin-left: auto;
}

@media (max-width: 768px) {
  .nav-tab {
    padding: 0 12px;
    font-size: 14px;

    &.active::after {
      left: 12px;
      right: 12px;
    }
  }
}
</style>
