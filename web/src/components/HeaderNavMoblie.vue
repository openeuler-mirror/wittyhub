<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import HeaderTheme from './HeaderTheme.vue'

const router = useRouter()
const route = useRoute()

const props = defineProps<{
  menuShow: boolean
}>()

const emit = defineEmits<{
  (e: 'link-click'): void
}>()

const navItems = [
  { name: '首页', path: '/', id: 'home' },
  { name: '探索', path: '/skills/search', id: 'search' },
  { name: '排行榜', path: '/skills/leaderboard', id: 'leaderboard' },
]

const navActive = ref('home')

watch(() => route.path, (val) => {
  const matched = navItems.find(item => {
    if (item.path === '/') return val === '/'
    return val.startsWith(item.path)
  })
  if (matched) navActive.value = matched.id
}, { immediate: true })

function handleNavClick(item: typeof navItems[0]) {
  navActive.value = item.id
  emit('link-click')
  router.push(item.path)
}
</script>

<template>
  <div class="header-content">
    <div class="header-nav" :class="{ active: menuShow }">
      <nav class="o-nav">
        <ul class="o-nav-list">
          <li
            v-for="item in navItems"
            :key="item.id"
            :class="{ active: navActive === item.id }"
          >
            <span @click="handleNavClick(item)">{{ item.name }}</span>
          </li>
        </ul>
      </nav>
      <div class="header-tool">
        <HeaderTheme />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@mixin nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  color: var(--o-color-info1, #1F2329);
  font-weight: 500;
  font-size: 16px;
  line-height: 24px;

  &.active {
    color: var(--o-color-primary1, #002FA7);
    background: var(--o-color-fill2, #F5F6F8);
  }
}

.header-content {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  height: 100%;

  .header-nav {
    flex: 1;
    justify-content: space-between;
    width: 100%;
    position: fixed;
    left: 0;
    overflow: hidden;
    top: 48px;
    height: calc(100vh - 48px);
    transform: translateX(-130%);
    transition-duration: 0.333s;
    transition-property: all;
    transition-timing-function: cubic-bezier(0.5, 0, 0.84, 0.25);
    display: block;
    z-index: 90;

    &.active {
      opacity: 1;
      visibility: visible;
      transform: translateX(0);
    }
  }
}

.header-tool {
  position: absolute;
  bottom: 36px;
  left: 0;
  width: 99px;
  display: flex;
  height: auto;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}

.o-nav {
  height: 100%;
  position: relative;
  width: 99px;
  background: var(--o-color-fill1, #FFFFFF);
  display: flex;
  flex-direction: column;
  justify-content: space-between;

  .o-nav-list {
    padding: 0;
    margin: 0;
    height: auto;
    font-size: 16px;
    line-height: 24px;
    font-weight: 500;

    > li {
      position: relative;
      text-align: center;
      @include nav-item;
    }
  }
}
</style>
