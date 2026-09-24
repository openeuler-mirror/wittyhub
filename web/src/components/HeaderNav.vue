<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { OTab, OTabPane } from '@opensig/opendesign'
import HeaderTheme from './HeaderTheme.vue'
import HeaderLogin from './HeaderLogin.vue'

const route = useRoute()
const router = useRouter()

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

const activeTab = computed(() => {
  const activeItem = navItems.find(isActive)
  return activeItem?.label || navItems[0].label
})

function onTabChange(value: string | number) {
  const item = navItems.find(navItem => navItem.label === String(value))
  if (item?.to && item.to !== route.path) router.push(item.to)
}
</script>

<template>
  <div class="header-nav">
    <!-- 主导航 tabs -->
    <OTab
      :model-value="activeTab"
      variant="text"
      size="small"
      :line="false"
      class="nav-tabs"
      @change="onTabChange"
    >
      <OTabPane v-for="item in navItems" :key="item.label" :value="item.label" :label="item.label" />
    </OTab>

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
  flex: 0 0 auto;
  align-self: stretch;
  height: 100%;
  --tab-nav-justify: flex-start;
  --tab-nav-gap: 40px;
  --tab-nav-padding: 0;
  --tab-nav-text-size: var(--o-font_size-text1);
  /* 与 AppHeader 中 SkillHub 标题的 20px / 26px 文字盒保持一致 */
  --tab-nav-text-height: var(--o-line_height-text2);
}

.nav-tabs :global(.o-tab-body) { display: none; }
.nav-tabs :global(.o-tab-head),
.nav-tabs :global(.o-tab-navs),
.nav-tabs :global(.o-tab-navs-container),
.nav-tabs :global(.o-tab-nav-list),
.nav-tabs :global(.o-tab-nav) {
  height: 100%;
}

.nav-tabs :global(.o-tab-nav) {
  box-sizing: border-box;
  transform: translateY(-10px);
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-font_size-text1);
  line-height: var(--o-line_height-text1);
  letter-spacing: 0;
  text-align: left;
  color: var(--o-color-info1);
}

.nav-tabs :global(.o-tab-nav-active) {
  font-weight: var(--o-font_weight-regular);
  color: var(--o-color-info1);
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
    --tab-nav-gap: 24px;
  }
}
</style>
