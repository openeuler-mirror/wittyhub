<script setup lang="ts">
import { computed } from 'vue'
import { useSkillStore } from '@/stores/skill'

const skillStore = useSkillStore()

const platformLabel: Record<string, string> = {
  openeuler: '社区官方',
  enterprise: '企业组织',
  personal: '个人'
}

const platformKeys = ['openeuler', 'enterprise', 'personal']

const providers = computed(() => {
  const platformCounts: Record<string, number> = {}
  for (const p of skillStore.stats?.platforms ?? []) {
    platformCounts[p.name] = p.count
  }
  return platformKeys.map(key => ({
    name: platformLabel[key],
    value: key,
    count: platformCounts[key] ?? 0
  }))
})

const allCategories = computed(() => skillStore.categories)

const securityLevels = computed(() => (skillStore.stats?.security_levels ?? []).filter(l => l.name !== '未检测'))

function toggleArrayItem(arr: string[], item: string): string[] {
  return arr.includes(item) ? arr.filter(i => i !== item) : [...arr, item]
}

const categoryNames: Record<string, string> = {
  Frontend: '前端',
  Networking: '网络',
  Database: '数据库',
  AI: 'AI',
  Mobile: '移动端',
  DevOps: 'DevOps',
  Backend: '后端',
  Data: '数据',
  Development: '开发工具',
  Design: '设计',
  Cloud: '云服务',
  Security: '安全',
  Others: '其他'
}

function displayCategory(name: string): string {
  return categoryNames[name] ?? name
}

function selectCategory(name: string) {
  skillStore.setFilter('category', toggleArrayItem(skillStore.filter.category, name))
  skillStore.fetchSkills()
}

function selectProvider(name: string) {
  const current = skillStore.filter.provider
  skillStore.setFilter(
    'provider',
    current.length === 1 && current[0] === name ? [] : [name]
  )
  skillStore.fetchSkills()
}

function selectSecurityLevel(name: string) {
  const current = skillStore.filter.securityLevel
  skillStore.setFilter(
    'securityLevel',
    current.length === 1 && current[0] === name ? [] : [name]
  )
  skillStore.fetchSkills()
}

function clearFilters() {
  skillStore.resetFilter()
  skillStore.fetchSkills()
}

const hasActiveFilter = computed(() => {
  const f = skillStore.filter
  return f.keyword || f.category.length > 0 || f.provider.length > 0 || f.securityLevel.length > 0
})
</script>

<template>
  <aside class="w-56 flex-shrink-0 hidden lg:block">
    <div class="space-y-6">
      <div>
        <h3 class="filter-section-title">贡献者</h3>
        <div class="space-y-[1px]">
          <div
            v-for="p in providers"
            :key="p.value"
            class="filter-item"
            :class="{ 'filter-item-active': skillStore.filter.provider.includes(p.value) }"
            @click="selectProvider(p.value)"
          >
            <span class="filter-item-label">
              <span class="filter-radio" :class="{ 'filter-radio-active': skillStore.filter.provider.includes(p.value) }">
              </span>
              {{ p.name }}
            </span>
            <span class="filter-count">{{ p.count }}</span>
          </div>
        </div>
      </div>

      <div>
        <h3 class="filter-section-title">分类</h3>
        <div class="space-y-[1px]">
          <div
            v-for="cat in allCategories"
            :key="cat.name"
            class="filter-item"
            :class="{ 'filter-item-active': skillStore.filter.category.includes(cat.name) }"
            @click="selectCategory(cat.name)"
          >
            <span class="filter-item-label">
              <span class="filter-checkbox" :class="{ 'filter-checkbox-active': skillStore.filter.category.includes(cat.name) }">
                <svg v-if="skillStore.filter.category.includes(cat.name)" class="filter-checkbox-icon" viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              {{ displayCategory(cat.name) }}
            </span>
            <span class="filter-count">{{ cat.count }}</span>
          </div>
        </div>
      </div>

      <div>
        <h3 class="filter-section-title">安全等级</h3>
        <div class="space-y-[1px]">
          <div
            v-for="level in securityLevels"
            :key="level.name"
            class="filter-item"
            :class="{ 'filter-item-active': skillStore.filter.securityLevel.includes(level.name) }"
            @click="selectSecurityLevel(level.name)"
          >
            <span class="filter-item-label">
              <span class="filter-radio" :class="{ 'filter-radio-active': skillStore.filter.securityLevel.includes(level.name) }">
              </span>
              {{ level.name }}
            </span>
            <span class="filter-count">{{ level.count }}</span>
          </div>
        </div>
      </div>

      <button v-if="hasActiveFilter" class="filter-clear" @click="clearFilters">
        清空筛选
      </button>
    </div>
  </aside>
</template>

<style scoped>
.filter-section-title {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: var(--o-r-font_size-text1);
  line-height: var(--o-r-line_height-text1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info4);
  margin-bottom: 12px;
}

[data-o-theme="e.dark"] .filter-section-title,
.dark .filter-section-title {
  color: #C9CDD4;
}

[data-o-theme="e.dark"] .filter-radio,
.dark .filter-radio {
  background-color: #242427;
}

[data-o-theme="e.dark"] .filter-radio-active::after,
.dark .filter-radio-active::after {
  background: #242427;
}

[data-o-theme="e.dark"] .filter-checkbox,
.dark .filter-checkbox {
  background-color: #242427;
}

.filter-item-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: var(--o-r-font_size-text1);
  line-height: var(--o-r-line_height-text1);
  letter-spacing: 0px;
  text-align: left;
  color: var(--o-color-info1);
}

.filter-item-active .filter-item-label {
  font-weight: var(--o-font_weight-semibold);
  color: var(--o-color-primary1);
}

.filter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: var(--o-radius-s);
  cursor: pointer;
  font-size: var(--o-r-font_size-tip1);
  line-height: var(--o-r-line_height-tip1);
  color: var(--o-color-info1);
  transition: all var(--o-duration-s) var(--o-easing-standard);
  user-select: none;
}

.filter-item:hover {
  background: var(--o-color-control2-light);
  border-radius: 8px;
}

.filter-item-active:hover {
  background-color: #CEDBF5;
  border-radius: var(--o-radius-s);
}

[data-o-theme="e.dark"] .filter-item:hover,
.dark .filter-item:hover {
  background: #2B2B2F;
}

.filter-item-active {
  color: var(--o-color-primary1);
  font-weight: var(--o-font_weight-medium);
  background-color: #CEDBF5;
  border-radius: var(--o-radius-s);
}

[data-o-theme="e.dark"] .filter-item-active:hover,
.dark .filter-item-active:hover {
  background-color: #353539;
}

[data-o-theme="e.dark"] .filter-item-active,
.dark .filter-item-active {
  background-color: #353539;
}

.filter-count {
  font-size: var(--o-r-font_size-tip2);
  color: var(--o-color-info3);
}

.filter-item-active .filter-count {
  color: var(--o-color-primary1);
}

.filter-radio {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid var(--o-color-control1);
  background-color: var(--o-color-white);
  flex-shrink: 0;
  transition: all var(--o-duration-s) var(--o-easing-standard);
}

.filter-radio-active {
  border: 4px solid var(--o-color-primary1);
  background-color: var(--o-color-primary1);
}

.filter-radio-active::after {
  content: '';
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--o-color-white);
  border: 1px solid var(--o-color-control4);
}

.filter-checkbox {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid var(--o-color-control1);
  background-color: var(--o-color-white);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--o-duration-s) var(--o-easing-standard);
}

.filter-checkbox-active {
  background-color: var(--o-color-primary1);
  border-color: var(--o-color-primary1);
}

.filter-checkbox-icon {
  width: 10px;
  height: 10px;
}

.filter-clear {
  width: 100%;
  text-align: left;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
  cursor: pointer;
  transition: color var(--o-duration-s) var(--o-easing-standard);
  padding: 4px 0;
  border: none;
  background: none;
}

.filter-clear:hover {
  color: var(--o-color-primary2);
}
</style>
