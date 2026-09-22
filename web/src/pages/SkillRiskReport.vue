<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import type { AuditReport, AuditReportStats } from '@/api/types'
import { useAppStore } from '@/stores/app'
import heroBgLight from '@/assets/bg/hero-top-texture.png'
import heroBgDark from '@/assets/bg/hero-top-texture-dark.png'
import emptyIllustration from '@/assets/images/empty-audit-report.png'
import RiskDetectionTable from '@/components/RiskDetectionTable.vue'
import { OBreadcrumb, OBreadcrumbItem, OLoading } from '@opensig/opendesign'
import { oaReport } from '@opendesign-plus/plugins/analytics'

const route = useRoute()
const appStore = useAppStore()

const skillId = decodeURIComponent((route.params.skillId as string) || '')
const report = ref<AuditReport | null>(null)
const loading = ref(true)
const error = ref('')

// 等级视觉映射（与详情页一致：安全绿 / 低风险蓝 / 中风险橙 / 高风险红）
const LEVEL_COLORS: Record<string, string> = {
  safe: 'var(--o-color-success1)',
  low: '#497AF8',
  medium: 'var(--o-color-warning1)',
  high: 'var(--o-color-danger1)',
  unknown: 'var(--o-color-info3)'
}
const levelColor = computed(() => LEVEL_COLORS[report.value?.level || 'unknown'] || LEVEL_COLORS.unknown)

// 得分仪表盘：160px 圆环、12 点起顺时针，圆弧角度 = 得分 ÷ 100 × 360°
// 0 分不绘制圆弧，100 分绘制整圆，其余得分按角度精确对应（得分变化时自动重算）
const reportScore = computed(() => {
  const score = report.value?.score
  return typeof score === 'number' ? Math.min(Math.max(score, 0), 100) : null
})
const gaugeFull = computed(() => reportScore.value === 100)
const gaugeArc = computed(() => {
  const score = reportScore.value
  // 未检测 / 0 分不绘制圆弧；100 分由整圆元素绘制
  if (score === null || score <= 0 || score >= 100) return ''
  const angle = score * 3.6
  const rad = (angle * Math.PI) / 180
  const x = (80 + 72 * Math.sin(rad)).toFixed(2)
  const y = (80 - 72 * Math.cos(rad)).toFixed(2)
  return `M 80 8 A 72 72 0 ${angle > 180 ? 1 : 0} 1 ${x} ${y}`
})

// 分类进度条：高 / 中 / 低风险色块长度与命中项数量严格成正比（百分比保留两位小数）
// 四个分类卡片共用同一比例映射规则；无命中项时整条显示品牌底色
function barSegments(stats: AuditReportStats | null | undefined): Array<{ color: string; width: string }> {
  const high = stats?.high ?? 0
  const medium = stats?.medium ?? 0
  const low = stats?.low ?? 0
  const total = stats?.total ?? 0
  if (total <= 0) {
    return [{ color: 'rgb(var(--o-brand-1))', width: '100.00%' }]
  }
  const ratio = (count: number) => `${((count / total) * 100).toFixed(2)}%`
  return [
    { color: 'var(--o-color-danger1)', width: ratio(high) },
    { color: 'var(--o-color-warning1)', width: ratio(medium) },
    { color: '#497AF8', width: ratio(low) }
  ]
}

function formatTime(value: string | null): string {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const metaLine = computed(() => {
  const parts: string[] = []
  if (report.value?.generated_at) parts.push(`报告生成时间：${formatTime(report.value.generated_at)}`)
  if (report.value?.engine) {
    const version = report.value.engine_version ? `-v${report.value.engine_version}` : ''
    parts.push(`评估引擎版本：${report.value.engine}${version}`)
  }
  parts.push(`检测项：${report.value?.rule_count ?? 0}`)
  return parts.join('   |   ')
})

const displaySkillName = computed(() => report.value?.skill_name || '')

onMounted(async () => {
  if (!skillId) {
    error.value = '缺少 Skill ID'
    loading.value = false
    return
  }
  loading.value = true
  try {
    report.value = await api.getSkillAuditReport(skillId)
    oaReport('risk_report_view', {
      module: 'skill_risk_report',
      skill_id: report.value.skill_id,
      has_report: report.value.has_report
    })
  } catch (e: any) {
    console.error('加载风险评估报告失败:', e)
    error.value = e?.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="report-page">
    <!-- 顶部纹理（与详情页/设计稿同一张 hero 底纹，覆盖顶部 450px） -->
    <div class="hero-texture">
      <img :src="appStore.isDark ? heroBgDark : heroBgLight" alt="" />
    </div>

    <div class="container-wide">
      <!-- 面包屑 -->
      <div class="breadcrumb-wrap">
        <OBreadcrumb
          style="
            --breadcrumb-text-size: 14px;
            --breadcrumb-text-height: 22px;
            --breadcrumb-separator-size: 24px;
            --breadcrumb-gap: 4px;
          "
        >
          <OBreadcrumbItem to="/">SkillHub</OBreadcrumbItem>
          <OBreadcrumbItem :to="`/skills/${encodeURIComponent(skillId)}`">
            {{ displaySkillName || 'Skill 详情' }}
          </OBreadcrumbItem>
          <OBreadcrumbItem>风险评估报告</OBreadcrumbItem>
        </OBreadcrumb>
      </div>

      <!-- 标题 + 报告元信息 -->
      <div class="report-header">
        <h1 class="report-title">{{ displaySkillName }} 风险评估报告</h1>
        <p v-if="report?.has_report" class="report-meta">{{ metaLine }}</p>
      </div>

      <!-- 加载态 -->
      <div v-if="loading" class="state-card">
        <OLoading v-model:visible="loading" size="medium" />
      </div>

      <!-- 错误态 -->
      <div v-else-if="error" class="state-card error-card">
        <p class="error-text">{{ error }}</p>
      </div>

      <template v-else-if="report">
        <!-- 无报告（尚未审计 / 报告不可用） -->
        <section v-if="!report.has_report" class="report-card empty-card">
          <h3 class="card-title">{{ report.reason === 'no_audit' ? '暂无安全审计记录' : '风险评估报告暂不可用' }}</h3>
          <div class="card-divider"></div>
          <div class="table-empty">
            <img :src="emptyIllustration" alt="" class="empty-illustration" />
            <p class="empty-text">
              {{ report.reason === 'no_audit' ? '该 Skill 尚未完成安全审计，请稍后再试' : '审计引擎未产出可解析的报告，请稍后再试' }}
            </p>
          </div>
        </section>

        <template v-else>
          <!-- ========== 整体评估摘要 ========== -->
          <section class="report-card summary-card">
            <h3 class="card-title">整体评估摘要</h3>
            <div class="card-divider"></div>
            <p class="summary-text">{{ report.summary }}</p>
          </section>

          <div class="report-row">
            <!-- ========== 综合风险得分 ========== -->
            <section class="report-card score-card">
              <h3 class="card-title">综合风险得分</h3>
              <div class="card-divider"></div>

              <div class="score-body">
                <div class="gauge">
                  <svg class="gauge-svg" viewBox="0 0 160 160">
                    <circle class="gauge-track" cx="80" cy="80" r="72" />
                    <!-- 满分：完整圆环 -->
                    <circle
                      v-if="gaugeFull"
                      class="gauge-arc"
                      cx="80"
                      cy="80"
                      r="72"
                      transform="rotate(-90 80 80)"
                      :style="{ stroke: levelColor }"
                    />
                    <!-- 其余得分：按得分百分比绘制弧 -->
                    <path
                      v-else-if="gaugeArc"
                      class="gauge-arc"
                      :d="gaugeArc"
                      :style="{ stroke: levelColor }"
                    />
                  </svg>
                  <div class="gauge-center">
                    <span class="gauge-score">{{ report.score ?? '-' }}</span>
                    <span class="gauge-label">风险得分</span>
                  </div>
                </div>

                <div class="level-block">
                  <span class="level-name" :style="{ color: levelColor }">{{ report.level_label }}</span>
                  <span class="level-desc">{{ report.level_description }}</span>
                </div>
              </div>

              <div class="score-meta">
                <div class="score-meta-row">
                  <span class="score-meta-label">评分标准</span>
                  <span class="score-meta-value">基于 NVIDIA SkillSpector，0-100 分数越高越危险</span>
                </div>
                <div class="score-meta-row">
                  <span class="score-meta-label">等级划分</span>
                  <span class="legend">
                    <span class="legend-item">
                      <i class="legend-dot" style="background: var(--o-color-success1)"></i>0-20 分：安全
                    </span>
                    <span class="legend-item">
                      <i class="legend-dot" style="background: #497af8"></i>21-50 分：低风险
                    </span>
                    <span class="legend-item">
                      <i class="legend-dot" style="background: var(--o-color-warning1)"></i>51-80 分：中风险
                    </span>
                    <span class="legend-item">
                      <i class="legend-dot" style="background: var(--o-color-danger1)"></i>81-100 分：高风险
                    </span>
                  </span>
                </div>
              </div>
            </section>

            <!-- ========== 风险分类 ========== -->
            <section class="report-card category-card">
              <div class="card-head">
                <h3 class="card-title">风险分类</h3>
                <div class="category-counts">
                  <span class="count-item">
                    <span class="count-num count-danger">{{ report.stats?.high ?? 0 }}</span>高风险
                  </span>
                  <span class="count-item">
                    <span class="count-num count-warning">{{ report.stats?.medium ?? 0 }}</span>中风险
                  </span>
                  <span class="count-item">
                    <span class="count-num count-blue">{{ report.stats?.low ?? 0 }}</span>低风险
                  </span>
                  <span class="count-item">
                    <span class="count-num count-total">{{ report.rule_count }}</span>检测项
                  </span>
                </div>
              </div>
              <div class="card-divider"></div>

              <div class="category-grid">
                <div v-for="category in report.categories" :key="category.key" class="category-item">
                  <div class="category-item-head">
                    <span class="category-item-name">{{ category.name }}</span>
                    <span
                      class="category-item-dims"
                      :title="`${category.dimension_count}个维度：${category.dimensions.map((dim) => dim.name).join('、')}`"
                    >{{ category.dimension_count }}个维度</span>
                  </div>
                  <p class="category-item-desc">{{ category.description }}</p>
                  <div class="category-bar">
                    <span
                      v-for="(segment, index) in barSegments(category.stats)"
                      :key="index"
                      :style="{ background: segment.color, width: segment.width }"
                    ></span>
                  </div>
                  <div class="category-legend">
                    <span class="legend-item">
                      <i class="legend-dot" style="background: var(--o-color-danger1)"></i>{{ category.stats.high }} 高
                    </span>
                    <span class="legend-item">
                      <i class="legend-dot" style="background: var(--o-color-warning1)"></i>{{ category.stats.medium }} 中
                    </span>
                    <span class="legend-item">
                      <i class="legend-dot" style="background: #497af8"></i>{{ category.stats.low }} 低
                    </span>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- ========== 风险检测详情（维度 -> 检测项聚合 + 展开 issue 定位） ========== -->
          <RiskDetectionTable
            :dimensions="report.dimensions"
            :findings="report.findings"
            :findings-truncated="report.findings_truncated"
          />
        </template>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.report-page {
  position: relative;
  min-height: 100vh;
  padding-bottom: 64px;
  /* 不额外刷底色：与 body 底色（--color-bg）保持一致，避免页面盒子底边出现色差分界线 */
  background: transparent;
}

/* ===== 顶部纹理 ===== */
.hero-texture {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 450px;
  overflow: hidden;
  pointer-events: none;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.container-wide {
  position: relative;
  max-width: 1488px;
  margin: 0 auto;
}

/* ===== 面包屑 ===== */
.breadcrumb-wrap {
  padding-top: 40px;
  margin-bottom: 40px;

  --breadcrumb-color: #00000099;

  :deep(.o-breadcrumb-item-label) {
    font-family: HarmonyHeiTi;
    font-weight: var(--o-font_weight-regular);
    letter-spacing: 0px;
    color: var(--breadcrumb-color);
    transition: color 0.2s;
  }

  :deep(.o-breadcrumb-item-label[href]),
  :deep(.o-breadcrumb-item a) {
    cursor: pointer;

    &:hover .o-breadcrumb-item-label {
      color: var(--o-color-primary1);
    }
  }

  /* 末级（当前页）：品牌色 + 半粗，与设计稿一致 */
  :deep(.o-breadcrumb-item:last-child .o-breadcrumb-item-label) {
    color: var(--o-color-primary1);
    font-weight: var(--o-font_weight-semibold);
  }

  :deep(.o-icon-chevron-right) {
    color: var(--breadcrumb-color);
  }
}

.dark .breadcrumb-wrap,
[data-o-theme="e.dark"] .breadcrumb-wrap {
  --breadcrumb-color: rgba(255, 255, 255, 0.6);
}

/* ===== 标题 + 元信息 ===== */
.report-header {
  margin-bottom: 32px;
}

.report-title {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: 48px;
  line-height: 64px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.report-meta {
  margin: 12px 0 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
}

/* ===== 卡片容器 ===== */
.report-card {
  background: var(--o-color-fill2);
  border-radius: 4px;
  padding: 24px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

/* 摘要正文：HarmonyHeiTi 16/24、regular、字间距 0，颜色为设计稿的 60% 黑（rgba(0,0,0,.6)） */
.summary-text {
  margin: 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
}

/* ===== 得分 + 分类 一行 ===== */
.report-row {
  display: flex;
  gap: 32px;
  margin-top: 32px;

  .score-card {
    width: 564px;
    flex-shrink: 0;
  }

  .category-card {
    flex: 1;
    min-width: 0;
  }
}

/* 得分仪表盘 */
.score-body {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
}

.gauge {
  position: relative;
  width: 160px;
  height: 160px;
  flex-shrink: 0;
}

.gauge-svg {
  width: 160px;
  height: 160px;
  display: block;
}

.gauge-track {
  fill: none;
  stroke: rgb(var(--o-brand-1));
  stroke-width: 16;
}

.gauge-arc {
  fill: none;
  stroke-width: 16;
  stroke-linecap: butt;
}

.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
}

.gauge-score {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: 28px;
  line-height: 40px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.gauge-label {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
}

.level-block {
  width: max-content;
  min-width: 144px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.level-name {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: 40px;
  line-height: 56px;
  letter-spacing: 0px;
}

.level-desc {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  text-align: center;
  color: var(--o-color-info3);
  white-space: nowrap;
}

.score-meta {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.score-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: HarmonyHeiTi;
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
}

.score-meta-label {
  flex-shrink: 0;
  color: var(--o-color-info1);
}

.score-meta-value {
  color: var(--o-color-info3);
}

.legend {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: HarmonyHeiTi;
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  color: var(--o-color-info2);
  white-space: nowrap;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 风险分类（右上角计数：数字着色 + 灰色标签，与设计稿一致） */
.category-counts {
  display: flex;
  align-items: center;
  gap: 16px;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  /* 标签文字：设计稿值为 #666666，即 --o-color-info3（60% 黑） */
  color: var(--o-color-info3);

  .count-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }

  /* 数字：半粗 + 语义色 */
  .count-num {
    font-weight: var(--o-font_weight-semibold);
  }

  .count-danger {
    color: var(--o-color-danger1);
  }

  .count-warning {
    color: var(--o-color-warning1);
  }

  /* 低风险蓝：设计稿定值 #497AF8（浅色主题下无同名语义 token） */
  .count-blue {
    color: #497af8;
  }

  .count-total {
    color: var(--o-color-info1);
  }
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.category-item {
  box-sizing: border-box;
  height: 120px;
  padding: 12px;
  border: 1px solid var(--o-color-control1);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.category-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.category-item-name {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-semibold);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: 0px;
  color: var(--o-color-info1);
}

.category-item-dims {
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
  white-space: nowrap;
}

.category-item-desc {
  margin: 8px 0 0;
  font-family: HarmonyHeiTi;
  font-weight: var(--o-font_weight-regular);
  font-size: 12px;
  line-height: 18px;
  letter-spacing: 0px;
  color: var(--o-color-info3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.category-bar {
  display: flex;
  height: 8px;
  margin-top: 8px;

  /* 段宽由 barSegments 按命中项数量计算（百分比保留两位小数），此处不做二次分配 */
  span {
    height: 8px;
    flex: 0 0 auto;
    transition: width 0.2s;
  }
}

.category-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;

  .legend-item {
    color: var(--o-color-info2);
  }
}

/* ===== 空态 / 状态卡片 ===== */
.state-card {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  background: var(--o-color-fill2);
  border-radius: 4px;

  &.error-card {
    min-height: 200px;
  }

  .error-text {
    color: var(--o-color-danger1);
    font-size: var(--o-r-font_size-text1);
  }
}

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

.empty-card {
  .table-empty {
    height: 320px;
  }
}
</style>