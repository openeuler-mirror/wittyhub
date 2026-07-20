<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import { useAppStore } from './stores/app'
import { onMounted } from 'vue'

const appStore = useAppStore()

onMounted(() => {
  appStore.initTheme()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#F5F6F8] dark:bg-[#111421]">
    <AppHeader />
    <main class="flex-1 pt-20 md:pt-20 pt-12">
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>
