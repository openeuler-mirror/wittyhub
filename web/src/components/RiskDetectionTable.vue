<script setup lang="ts">
/**
 * 风险检测详情（报告页的下半部分，从 SkillRiskReport 抽出）。
 *
 * 行 = 检测项（维度 -> 检测项聚合），风险维度列取所属维度中文名；展开后逐条列出
 * 该检测项命中的 issue 定位路径。筛选与展开态由本组件维护，数据由父组件传入。
 */
import { computed, ref } from 'vue'
import type { AuditReportDimension, AuditReportFinding, AuditReportStats } from '@/api/types'
import chevronDownSvg from '@/assets/icons/chevron-down.svg?raw'
import fileCodeSvg from '@/assets/icons/file-code.svg?raw'
import emptyIllustration from '@/assets/images/empty-audit-report.png'

const props = defineProps<{
  /** 按 17 维度聚合的命中项（接口 dimensions） */
  dimensions: AuditReportDimension[]
  /** 逐条风险明细（接口 findings） */
  findings: AuditReportFinding[]
  /** 明细是否被截断（统计仍为全量） */
  findingsTruncated?: boolean
}>()

// 分类 / 等级 筛选（单选，语义与设计稿“风险检测详情”一致）
const CATEGORY_TABS = [
  { key: 'all', label: '全部' },
  { key: 'prompt', label: '提示操控类' },
  { key: 'data', label: '数据泄露类' },
  { key: 'privilege_code', label: '权限与代码执行类' },
  { key: 'supply_chain', label: '供应链风险类' }
]
const LEVEL_TABS = [
  { key: 'all', label: '全部' },
  { key: 'high', label: '高风险' },
  { key: 'medium', label: '中风险' },
  { key: 'low', label: '低风险' }
]
const activeCategory = ref('all')
const activeLevel = ref('all')
// 展开态：支持同时展开多个检测项（用 Set 记录已展开的行 key）
const expandedKeys = ref<Set<string>>(new Set())

/** 详情表的行：维度 -> 检测项（每行一个检测项，风险维度列取所属维度中文名） */
interface DetailRow {
  key: string
  ruleId: string
  ruleName: string
  dimension: string
  dimensionKey: string
  categoryKey: string
  stats: AuditReportStats
  maxSeverityGroup: 'high' | 'medium' | 'low'
  remediation: string | null
}

const detailRows = computed<DetailRow[]>(() =>
  (props.dimensions || []).flatMap((dimension) =>
    (dimension.rules || []).map((rule) => ({
      key: `${dimension.key}:${rule.rule_id || rule.rule_name || 'unknown'}`,
      ruleId: rule.rule_id,
      ruleName: rule.rule_name || rule.rule_id || dimension.name,
      dimension: dimension.name,
      dimensionKey: dimension.key,
      categoryKey: dimension.category_key,
      stats: rule.stats,
      maxSeverityGroup: rule.max_severity_group,
      remediation: rule.remediation
    }))
  )
)

// 分类筛检测项所属大类；等级筛该检测项内是否含该等级的命中项
const filteredRows = computed(() =>
  detailRows.value.filter(
    (row) =>
      (activeCategory.value === 'all' || row.categoryKey === activeCategory.value) &&
      (activeLevel.value === 'all' || row.stats[activeLevel.value as 'high' | 'medium' | 'low'] > 0)
  )
)

/** 某检测项下命中的具体 issue（展开后的下拉明细，每个 issue 一行） */
function issuesOfRule(row: DetailRow): AuditReportFinding[] {
  return (props.findings || []).filter(
    (item) => item.dimension_key === row.dimensionKey && item.rule_id === row.ruleId
  )
}

function toggleRow(key: string) {
  if (expandedKeys.value.has(key)) expandedKeys.value.delete(key)
  else expandedKeys.value.add(key)
}

/** issue 定位路径：`文件:起始行-结束行`（单行只保留起始行） */
function issueLocation(item: AuditReportFinding): string {
  const { file, start_line: start, end_line: end } = item.location || {}
  if (!file) return '未知位置'
  if (start == null) return file
  return end != null && end !== start ? `${file}:${start}-${end}` : `${file}:${start}`
}

const SEVERITY_LABELS: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险' }
const SEVERITY_TAG_CLASS: Record<string, string> = { high: 'tag-danger', medium: 'tag-warning', low: 'tag-blue' }
const STATUS_LABELS: Record<string, string> = { open: '需修复', fixed: '已修复', ignored: '已忽略' }

function severityLabel(group: string): string {
  return SEVERITY_LABELS[group] || group
}
function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status
}
</script>

<template>
  <section class="report-card detail-card">
    <h3 class="card-title">风险检测详情</h3>
    <div class="card-divider"></div>

    <div class="filters">
      <div class="filter-row">
        <span class="filter-label">分类</span>
        <div class="filter-chips">
          <button
            v-for="tab in CATEGORY_TABS"
            :key="tab.key"
            class="chip"
            :class="{ 'is-active': activeCategory === tab.key }"
            type="button"
            @click="activeCategory = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
      <div class="filter-row">
        <span class="filter-label">等级</span>
        <div class="filter-chips">
          <button
            v-for="tab in LEVEL_TABS"
            :key="tab.key"
            class="chip"
            :class="{ 'is-active': activeLevel === tab.key }"
            type="button"
            @click="activeLevel = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
    </div>

    <template v-if="filteredRows.length">
      <div class="detail-table">
        <div class="table-head">
          <span class="col col-main">风险项</span>
          <span class="col col-remediation">修复建议</span>
          <span class="col col-dimension">风险维度</span>
          <span class="col col-level">等级</span>
          <span class="col col-status">状态</span>
        </div>

        <template v-for="row in filteredRows" :key="row.key">
          <div class="table-row" :class="{ 'is-expanded': expandedKeys.has(row.key) }">
            <span class="col col-main">
              <button
                class="row-toggle"
                :class="{ 'is-open': expandedKeys.has(row.key) }"
                type="button"
                :aria-label="expandedKeys.has(row.key) ? '收起' : '展开'"
                @click="toggleRow(row.key)"
              >
                <span class="row-toggle-icon" v-html="chevronDownSvg"></span>
              </button>
              <span class="cell-text">{{ row.ruleName }}</span>
              <span class="count-badge">{{ row.stats.total }} 项</span>
            </span>
            <span class="col col-remediation"><span class="cell-text">{{ row.remediation || '-' }}</span></span>
            <span class="col col-dimension"><span class="cell-text">{{ row.dimension }}</span></span>
            <span class="col col-level">
              <span class="level-tag" :class="SEVERITY_TAG_CLASS[row.maxSeverityGroup]">
                {{ severityLabel(row.maxSeverityGroup) }}
              </span>
            </span>
            <span class="col col-status">{{ statusLabel('open') }}</span>
          </div>

          <!-- 展开：该检测项下每个 issue 一行（仅展示完整定位路径） -->
          <div v-if="expandedKeys.has(row.key)" class="issue-list">
            <div
              v-for="(issue, index) in issuesOfRule(row)"
              :key="`${issue.rule_id}-${index}`"
              class="issue-line"
            >
              <span class="issue-icon" v-html="fileCodeSvg"></span>
              <span class="issue-location">{{ issueLocation(issue) }}</span>
            </div>
          </div>
        </template>
      </div>
      <p v-if="findingsTruncated" class="truncate-hint">风险明细过多，仅展示部分内容（统计仍为全量）</p>
    </template>

    <!-- 空态（无匹配风险项 / 无风险项） -->
    <div v-else class="table-empty">
      <img :src="emptyIllustration" alt="" class="empty-illustration" />
      <p class="empty-text">当前筛选条件下无风险项</p>
    </div>
  </section>
</template>

<style lang="scss" scoped>
/* ===== 卡片容器（与页面其它卡片一致） ===== */
.report-card {
  background: var(--o-color-fill2);
  border-radius: 4px;
  padding: 24px;
}

.card-title {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: 22px;
  line-height: 30px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.card-divider {
  height: 1px;
  background: var(--o-color-control4);
  margin: 24px 0;
}

/* ===== 风险检测详情 ===== */
.detail-card {
  margin-top: 32px;
}

.filters {
  display: flex;
  flex-direction: column;
  gap: 33px;
  margin-bottom: 24px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 40px;
}

.filter-label {
  flex-shrink: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-medium);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  box-sizing: border-box;
  height: 32px;
  padding: 0 16px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: var(--o-color-control2-light);
  color: var(--o-color-info1);
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  cursor: pointer;
  transition: color 0.2s, background-color 0.2s, border-color 0.2s;

  @include hover {
    color: var(--o-color-primary1);
  }

  &.is-active {
    border-color: var(--o-color-primary1);
    background: var(--o-color-fill2);
    color: var(--o-color-primary1);
  }
}

.detail-table {
  font-family: HarmonyHeiTi;
}

.table-head {
  display: flex;
  align-items: center;
  height: 38px;
  border-bottom: 1px solid var(--o-color-primary1);
  font-size: 14px;
  line-height: 22px;
  letter-spacing: 0px;
  font-weight: var(--o-font_weight-semibold);
  color: var(--o-color-info1);
}

.table-row {
  display: flex;
  align-items: center;
  height: 38px;
  border-bottom: 1px solid var(--o-color-control4);
  font-size: 14px;
  line-height: 22px;
  letter-spacing: 0px;
  font-weight: var(--o-font_weight-regular);
  color: var(--o-color-info1);

  &.is-expanded {
    background: var(--o-color-control3-light);
    border-bottom-color: transparent;
  }
}

.col {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  min-width: 0;
}

.col-main {
  width: 332px;
  flex-shrink: 0;
  gap: 8px;
  padding-left: 16px;
}

/* 表头「风险项」距表格左边界 48px（设计稿：与数据行检测项文字左对齐） */
.table-head .col-main {
  padding-left: 48px;
}

.col-remediation {
  width: 678px;
  flex-shrink: 0;
  padding-right: 16px;
}

.col-dimension {
  width: 182px;
  flex-shrink: 0;
}

.col-level {
  width: 92px;
  flex-shrink: 0;
}

.col-status {
  width: 156px;
  flex-shrink: 0;
}

.cell-text {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* 检测项聚合行：命中项数量徽标 */
.count-badge {
  box-sizing: border-box;
  flex-shrink: 0;
  height: 20px;
  padding: 0 6px;
  border-radius: 4px;
  background: var(--o-color-control2-light);
  color: var(--o-color-info2);
  font-size: 12px;
  line-height: 20px;
}

.row-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--o-color-info1);
  cursor: pointer;
  flex-shrink: 0;
}

.row-toggle-icon {
  display: inline-flex;
  width: 24px;
  height: 24px;

  :deep(svg) {
    width: 24px;
    height: 24px;
    display: block;
    transform: rotate(-90deg);
    transition: transform 0.2s;
  }
}

.row-toggle.is-open .row-toggle-icon :deep(svg) {
  transform: rotate(0deg);
}

.level-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 60px;
  height: 24px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  color: #ffffff;

  &.tag-danger {
    background: var(--o-color-danger1);
  }

  &.tag-warning {
    background: var(--o-color-warning1);
  }

  &.tag-blue {
    background: #497af8;
  }
}

/* 展开的 issue 明细：无左右缩进，行分隔线贯通表格整宽（设计稿） */
.issue-line {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  /* 设计稿：代码行内容起点 = 行文本起点（48px）+ 13px */
  padding-left: 61px;
  border-bottom: 1px solid var(--o-color-control4);
  font-size: 14px;
  line-height: 22px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.issue-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--o-color-info3);

  :deep(svg) {
    width: 16px;
    height: 16px;
    display: block;
  }

  :deep(path) {
    fill: currentColor;
    fill-opacity: 1;
  }
}

/* 定位路径：设计稿为灰色（info3），单行省略 */
.issue-location {
  min-width: 0;
  font-family: HarmonyHeiTi;
  font-size: 14px;
  line-height: 22px;
  color: var(--o-color-info3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.truncate-hint {
  margin: 12px 0 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--o-color-info3);
}

/* ===== 空态 ===== */
.table-empty {
  height: 461px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.empty-illustration {
  width: 320px;
  height: 280px;
  display: block;
}

.empty-text {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
}
</style>