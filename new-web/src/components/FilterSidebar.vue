<script setup lang="ts">
import { computed } from 'vue'
import { useSkillStore } from '@/stores/skill'

const skillStore = useSkillStore()

const providers = [
  { name: '社区官方', value: 'community', count: 126 },
  { name: '企业组织', value: 'enterprise', count: 468 },
  { name: '个人', value: 'individual', count: 231 }
]

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
  Security: '安全'
}

function displayCategory(name: string): string {
  return categoryNames[name] ?? name
}

function selectCategory(name: string) {
  skillStore.setFilter('category', toggleArrayItem(skillStore.filter.category, name))
  skillStore.fetchSkills()
}

function selectProvider(name: string) {
  skillStore.setFilter('provider', toggleArrayItem(skillStore.filter.provider, name))
  skillStore.fetchSkills()
}

function selectSecurityLevel(name: string) {
  skillStore.setFilter('securityLevel', toggleArrayItem(skillStore.filter.securityLevel, name))
  skillStore.fetchSkills()
}

function clearFilters() {
  skillStore.resetFilter()
  skillStore.fetchSkills()
}
</script>

<template>
  <aside class="w-56 flex-shrink-0 hidden lg:block">
    <div class="space-y-6">
      <div>
        <h3 class="filter-section-title">贡献者</h3>
        <div class="space-y-1">
          <div
            v-for="p in providers"
            :key="p.value"
            class="filter-item"
            :class="{ 'filter-item-active': skillStore.filter.provider.includes(p.value) }"
            @click="selectProvider(p.value)"
          >
            <span class="flex items-center gap-2">
              <span class="filter-checkbox" :class="{ 'filter-checkbox-active': skillStore.filter.provider.includes(p.value) }">
                <svg v-if="skillStore.filter.provider.includes(p.value)" class="filter-checkbox-icon" viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              {{ p.name }}
            </span>
            <span class="filter-count">{{ p.count }}</span>
          </div>
        </div>
      </div>

      <div>
        <h3 class="filter-section-title">分类</h3>
        <div class="space-y-1">
          <div
            v-for="cat in allCategories"
            :key="cat.name"
            class="filter-item"
            :class="{ 'filter-item-active': skillStore.filter.category.includes(cat.name) }"
            @click="selectCategory(cat.name)"
          >
            <span class="flex items-center gap-2">
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
        <div class="space-y-1">
          <div
            v-for="level in securityLevels"
            :key="level.name"
            class="filter-item"
            :class="{ 'filter-item-active': skillStore.filter.securityLevel.includes(level.name) }"
            @click="selectSecurityLevel(level.name)"
          >
            <span class="flex items-center gap-2">
              <span class="filter-checkbox" :class="{ 'filter-checkbox-active': skillStore.filter.securityLevel.includes(level.name) }">
                <svg v-if="skillStore.filter.securityLevel.includes(level.name)" class="filter-checkbox-icon" viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              {{ level.name }}
            </span>
            <span class="filter-count">{{ level.count }}</span>
          </div>
        </div>
      </div>

      <button class="filter-clear" @click="clearFilters">
        清空筛选
      </button>
    </div>
  </aside>
</template>

<style scoped>
.filter-section-title {
  font-family: HarmonyHeiTi;
  font-weight: 600;
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  text-align: left;
  color: #00000066;
  margin-bottom: 12px;
}

[data-o-theme="e.dark"] .filter-section-title,
.dark .filter-section-title {
  color: #C9CDD4;
}

.filter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: var(--o-radius_control-xs);
  cursor: pointer;
  font-size: 14px;
  line-height: 22px;
  color: var(--o-color-info1);
  transition: all var(--o-duration-s) var(--o-easing-standard);
  user-select: none;
}

.filter-item:hover {
  background-color: var(--o-color-control6);
}

.filter-item-active {
  color: var(--o-color-primary1);
  font-weight: 500;
  background-color: var(--o-color-control2-light);
}

.filter-count {
  font-size: 12px;
  color: var(--o-color-text3);
}

.filter-item-active .filter-count {
  color: var(--o-color-primary1);
}

.filter-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 2px solid var(--o-color-control4);
  flex-shrink: 0;
  transition: all var(--o-duration-s) var(--o-easing-standard);
}

.filter-checkbox-active {
  border-color: var(--o-color-primary1);
  background-color: var(--o-color-primary1);
}

.filter-checkbox-icon {
  width: 10px;
  height: 10px;
}

.filter-clear {
  width: 100%;
  text-align: center;
  font-size: 14px;
  line-height: 22px;
  color: var(--o-color-primary1);
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
