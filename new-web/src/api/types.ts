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
  category: string | null
  tags: string[] | null
  platform: string | null
  content: string | null
  metadata: Record<string, any>
  security_score: number | null
  security_level?: string
  download_count: number
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

export interface DownloadResponse {
  download_url: string
  file_path: string | null
  security_audit: SecurityAudit | null
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
  released_at: string | null
  download_count: number
  install_command?: string
}

export interface Stats {
  total_skills: number
  total_categories: number
  categories: { name: string; count: number }[]
  platforms: { name: string; count: number }[]
  security_levels: { name: string; count: number }[]
}

export interface Category {
  name: string
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
