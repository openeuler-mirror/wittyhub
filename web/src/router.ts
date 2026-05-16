import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/pages/Home.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/skills/search',
      name: 'search',
      component: () => import('@/pages/Search.vue')
    },
    {
      path: '/skills/:repo/:name',
      name: 'skill-detail',
      component: () => import('@/pages/SkillDetail.vue')
    },
    {
      path: '/skills/categories/:category',
      name: 'category',
      component: () => import('@/pages/Category.vue')
    },
    {
      path: '/skills/leaderboard',
      name: 'leaderboard',
      component: () => import('@/pages/Leaderboard.vue')
    }
  ]
})

export default router