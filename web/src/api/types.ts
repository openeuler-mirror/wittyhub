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