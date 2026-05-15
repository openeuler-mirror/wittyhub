<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SearchBar from '@/components/SearchBar.vue'
import CategoryNav from '@/components/CategoryNav.vue'
import SkillCard from '@/components/SkillCard.vue'
import { api } from '@/api/client'
import type { Skill } from '@/api/types'

const trendingSkills = ref<Skill[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.listSkills({ limit: 6 })
    trendingSkills.value = res.skills
  } catch (e) {
    console.error('Failed to load skills:', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <!-- Hero Section -->
    <section class="bg-gradient-to-br from-primary-500 to-primary-700 text-white">
      <div class="max-w-7xl mx-auto px-4 py-16">
        <div class="text-center mb-8">
          <h1 class="text-4xl md:text-5xl font-bold mb-4">
            发现 AI Agent Skills
          </h1>
          <p class="text-xl text-primary-100 max-w-2xl mx-auto">
            探索、评估和获取可复用的 AI Agent Skills。支持关键词搜索、分类浏览、安全检测。
          </p>
        </div>
        <div class="max-w-2xl mx-auto">
          <SearchBar />
        </div>
      </div>
    </section>

    <!-- Categories -->
    <section class="max-w-7xl mx-auto px-4 py-12">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">分类浏览</h2>
      <CategoryNav />
    </section>

    <!-- Trending Skills -->
    <section class="max-w-7xl mx-auto px-4 py-12">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-900">热门 Skills</h2>
        <RouterLink
          to="/skills/search"
          class="text-primary-500 hover:text-primary-600 font-medium"
        >
          查看更多 →
        </RouterLink>
      </div>

      <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="card animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div class="h-3 bg-gray-100 rounded w-1/2 mb-4"></div>
          <div class="h-16 bg-gray-100 rounded"></div>
        </div>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <SkillCard v-for="skill in trendingSkills" :key="skill.id" :skill="skill" />
      </div>
    </section>

    <!-- Stats -->
    <section class="bg-gray-50 border-y border-gray-200">
      <div class="max-w-7xl mx-auto px-4 py-12">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div class="text-3xl font-bold text-primary-500">2236+</div>
            <div class="text-gray-500 text-sm mt-1">已收录 Skills</div>
          </div>
          <div>
            <div class="text-3xl font-bold text-primary-500">50+</div>
            <div class="text-gray-500 text-sm mt-1">涵盖分类</div>
          </div>
          <div>
            <div class="text-3xl font-bold text-primary-500">100%</div>
            <div class="text-gray-500 text-sm mt-1">开源免费</div>
          </div>
          <div>
            <div class="text-3xl font-bold text-primary-500">安全</div>
            <div class="text-gray-500 text-sm mt-1">安全检测</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>