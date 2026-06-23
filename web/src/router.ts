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
      path: '/skills/:path',
      name: 'skill-detail',
      component: () => import('@/pages/SkillDetail.vue')
    },
    {
      path: '/skills/:name',
      name: 'skill-detail-single',
      component: () => import('@/pages/SkillDetail.vue')
    },
    {
      path: '/skills/categories/:category',
      name: 'category',
      component: () => import('@/pages/Category.vue')
    },
    {
      path: '/leaderboard',
      name: 'leaderboard',
      component: () => import('@/pages/Leaderboard.vue')
    },
    {
      path: '/agents/',
      name: 'agent-list',
      component: () => import('@/pages/AgentList.vue')
    },
    {
      path: '/agents/:path',
      name: 'agent-detail',
      component: () => import('@/pages/AgentDetail.vue')
    }
  ]
})

export default router