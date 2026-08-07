import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import type { Skill, FilterState, Stats, Category } from '@/api/types'

export const useSkillStore = defineStore('skill', () => {
  const skills = ref<Skill[]>([])
  const total = ref(0)
  const loading = ref(false)
  const hasLoadedOnce = ref(false)
  const stats = ref<Stats | null>(null)
  const categories = ref<Category[]>([])

  const filter = ref<FilterState>({
    keyword: '',
    category: [],
    provider: [],
    securityLevel: [],
    sortBy: 'hot',
    sortPeriod: 'all',
    viewMode: 'card',
    page: 1,
    pageSize: 12
  })

  const totalPages = computed(() => Math.ceil(total.value / filter.value.pageSize))

  async function fetchSkills() {
    loading.value = true
    try {
      const params: any = {
        skip: (filter.value.page - 1) * filter.value.pageSize,
        limit: filter.value.pageSize
      }

      if (filter.value.category.length > 0) {
        params.category = filter.value.category.join(',')
      }

      if (filter.value.securityLevel.length > 0) {
        params.security_level = filter.value.securityLevel.join(',')
      }

      if (filter.value.provider.length > 0) {
        params.platform = filter.value.provider.join(',')
      }

      if (filter.value.sortBy === 'hot' || filter.value.sortBy === 'downloads') {
        params.sort_by = 'download_count'
        if (filter.value.sortPeriod && filter.value.sortPeriod !== 'all') {
          params.sort_period = filter.value.sortPeriod
        }
      } else if (filter.value.sortBy === 'latest') {
        params.sort_by = 'updated_at'
      }

      if (filter.value.keyword) {
        const res = await api.searchSkills({
          q: filter.value.keyword,
          mode: 'text',
          scope: 'summary',
          ...params
        })
        skills.value = res.results
        total.value = res.total
      } else {
        const res = await api.listSkills(params)
        skills.value = res.skills
        total.value = res.total
      }
    } catch (e) {
      console.error('Failed to fetch skills:', e)
    } finally {
      hasLoadedOnce.value = true
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const res = await api.getStats()
      stats.value = res
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  async function fetchCategories() {
    try {
      const res = await api.getCategories()
      categories.value = res.categories
    } catch (e) {
      console.error('Failed to fetch categories:', e)
    }
  }

  function setFilter(key: keyof FilterState, value: any) {
    (filter.value as any)[key] = value
    if (key !== 'page' && key !== 'pageSize' && key !== 'viewMode') {
      filter.value.page = 1
    }
  }

  function resetFilter() {
    filter.value = {
      keyword: '',
      category: [],
      provider: [],
      securityLevel: [],
      sortBy: 'hot',
      sortPeriod: 'all',
      viewMode: 'card',
      page: 1,
      pageSize: 12
    }
  }

  return {
    skills,
    total,
    loading,
    hasLoadedOnce,
    stats,
    categories,
    filter,
    totalPages,
    fetchSkills,
    fetchStats,
    fetchCategories,
    setFilter,
    resetFilter
  }
})
