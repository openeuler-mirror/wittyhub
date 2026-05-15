<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <header class="bg-white border-b border-gray-100 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <RouterLink to="/" class="flex items-center gap-2">
          <div class="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <span class="text-white font-bold text-sm">S</span>
          </div>
          <span class="text-xl font-semibold text-primary-500">SkillHub</span>
        </RouterLink>

        <nav class="hidden md:flex items-center gap-6">
          <RouterLink to="/" class="text-gray-600 hover:text-primary-500 transition-colors">首页</RouterLink>
          <RouterLink to="/skills/search" class="text-gray-600 hover:text-primary-500 transition-colors">探索</RouterLink>
          <RouterLink to="/skills/leaderboard" class="text-gray-600 hover:text-primary-500 transition-colors">排行榜</RouterLink>
        </nav>

        <div class="flex items-center gap-4">
          <RouterLink
            to="/skills/search"
            class="btn-primary text-sm"
          >
            搜索 Skill
          </RouterLink>
        </div>
      </div>
    </div>
  </header>
</template>