export type ResponseT<T> = {
  code: number
  msg: string
  data: T
}

export interface Skill {
  id: string
  skill_id: string
  name: string
  description: string | null
  version: string | null
  commit_id: string | null
  author: string | null
  source: string
  source_url: string
  repo_url: string | null
  category: string | null
  category_label?: string | null
  tags: string[] | null
  platform: string | null
  content: string | null
  metadata: Record<string, any>
  risk_score: number | null
  security_level?: string
  download_count: number
  period_downloads?: number | null
  rating: number | null
  created_at: string
  updated_at: string
  last_indexed_at: string | null
}

export interface SkillListResponse {
  skills: Skill[]
  total: number
  skip: number
  limit: number
}

export interface SearchResponse {
  results: Skill[]
  total: number
  query: string
  skip: number
  limit: number
  processing_time_ms: number
}

export interface SecurityAudit {
  id: string
  resource_type: string
  resource_id: string
  audit_type: string
  risk_level: string
  risk_signals: RiskSignal[]
  details: Record<string, any>
  audited_at: string
}

export interface RiskSignal {
  id: string
  name: string
  description: string
  severity: string
  data: Record<string, any>
}

/** 风险条数统计（按展示分组 high/medium/low） */
export interface AuditReportStats {
  high: number
  medium: number
  low: number
  total: number
}

/** 四大类下属的风险维度引用（分类 -> 维度层级关系） */
export interface AuditReportDimensionRef {
  key: string
  name: string
}

/** 风险分类聚合（提示操控类 / 数据泄露类 / 权限与代码执行类 / 供应链风险类） */
export interface AuditReportCategory {
  key: string
  name: string
  description: string
  dimension_count: number
  dimensions: AuditReportDimensionRef[]
  stats: AuditReportStats
}

/** 维度下的检测项聚合（“风险检测详情”的行：检测项 -> 命中项） */
export interface AuditReportRuleRow {
  rule_id: string
  rule_name: string | null
  stats: AuditReportStats
  max_severity_group: 'high' | 'medium' | 'low'
  remediation: string | null
}

/** 按风险维度聚合的命中项（“风险检测详情”的聚合行） */
export interface AuditReportDimension {
  key: string
  name: string
  category_key: string
  description: string
  /** 该维度命中的检测项（规则 ID，如表 AST4、TT5） */
  rule_ids: string[]
  /** 该维度下按检测项聚合的行 */
  rules: AuditReportRuleRow[]
  stats: AuditReportStats
  max_severity_group: 'high' | 'medium' | 'low'
  remediation: string | null
}

export interface AuditReportLocation {
  file: string | null
  start_line: number | null
  end_line: number | null
}

/** 一条风险明细（“风险检测详情”展开后的 issue 行，文案为中文） */
export interface AuditReportFinding {
  id: string
  rule_id: string
  rule_name: string | null
  title: string
  dimension: string
  dimension_key: string
  category_key: string
  severity: string
  severity_group: 'high' | 'medium' | 'low'
  status: string
  remediation: string | null
  location: AuditReportLocation | null
  code_snippet: string | null
  truncated: boolean
}

/** Skill 风险评估报告（详情页「查看风险评估报告」数据源） */
export interface AuditReport {
  skill_id: string
  skill_name: string
  source_url: string | null
  repo_url: string | null
  version: string | null
  has_report: boolean
  reason: string | null
  generated_at: string | null
  engine: string | null
  engine_version: string | null
  score: number | null
  level: string | null
  level_label: string | null
  level_description: string | null
  recommendation: string | null
  summary: string | null
  /** 规则目录规模（“检测项”总数，静态值） */
  rule_count: number
  stats: AuditReportStats | null
  categories: AuditReportCategory[]
  dimensions: AuditReportDimension[]
  findings: AuditReportFinding[]
  findings_truncated: boolean
}

export interface DownloadResponse {
  blob: Blob
  filename: string
}

export interface SkillVersionsResponse {
  source_url: string
  skill_id: string
  versions: SkillVersion[]
}

export interface SkillVersion {
  version: string
  commit_id: string | null
  author: string | null
  message: string | null
  created_at: string
  download_count: number
  install_command?: string
  content: string | null
}

export interface ContributorSkillsResponse {
  source: string
  author: string
  platform: string | null
  name: string | null
  description: string | null
  git_profile: string | null
  website: string | null
  skill_count: number
  total_downloads: number
  skills: Skill[]
  total: number
  skip: number
  limit: number
}

export interface Contributor {
  id: string
  source: string
  author: string
  platform: string | null
  name: string | null
  description: string | null
  avatar_url: string | null
  git_profile: string | null
  website: string | null
  repo_url: string | null
  skill_count: number
  total_downloads: number
  created_at: string
  updated_at: string
}

export interface ContributorListResponse {
  contributors: Contributor[]
  total: number
  grand_total: number
  skip: number
  limit: number
  platform_counts: Record<string, number>
}

export interface Stats {
  total_skills: number
  total_categories: number
  total_downloads: number
  categories: Category[]
  platforms: { name: string; count: number }[]
  security_levels: { name: string; count: number }[]
}

export interface Category {
  name: string
  label?: string
  count: number
}

export interface FilterState {
  keyword: string
  category: string[]
  provider: string[]
  securityLevel: string[]
  sortBy: 'hot' | 'latest' | 'downloads'
  sortPeriod: 'all' | 'week' | 'month'
  viewMode: 'card' | 'list'
  page: number
  pageSize: number
}
