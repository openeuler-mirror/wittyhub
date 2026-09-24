<script setup lang="ts">
import { useRoute } from 'vue-router'
import { OLink } from '@opensig/opendesign'
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
      <OLink
        v-for="item in navItems"
        :key="item.label"
        :to="item.to"
        :class="['nav-tab', { active: isActive(item) }]"
        color="normal"
        :hover-underline="false"
      >{{ item.label }}</OLink>
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
  align-items: center;
  flex: 0 0 auto;
  height: 100%;
  gap: 40px;
}

.nav-tab {
  display: inline-flex;
  align-items: center;
  height: 100%;
  padding: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text1);
  line-height: var(--o-line_height-text1);
  letter-spacing: 0;
  text-align: left;
  color: var(--o-color-info1);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color var(--o-duration-m1, 0.2s) var(--o-easing-standard, ease),
    border-color var(--o-duration-m1, 0.2s) var(--o-easing-standard, ease);

  &:hover,
  &.active {
    color: var(--o-color-info1);
    border-bottom-color: var(--o-color-primary1);
  }
}

.header-tool {
  display: flex;
  align-items: center;
  height: 100%;
  margin-left: auto;
}

@media (max-width: 768px) {
  .nav-tabs {
    max-width: 60%;
    gap: 24px;
  }
}
</style>
