import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/pages/Home.vue'
import SkillDetail from '@/pages/SkillDetail.vue'

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
      component: Home
    },
    {
      path: '/skills/categories/:category',
      name: 'category',
      component: Home
    },
    {
      path: '/skills/:skillId(.*)',
      name: 'skill-detail',
      component: SkillDetail
    }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

export default router
