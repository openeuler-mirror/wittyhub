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

export interface ParsedConfigPromptIdentity {
  role?: string
  emoji?: string
  vibe?: string
}

export interface ParsedConfigPrompt {
  system?: string
  identity?: ParsedConfigPromptIdentity
  workflow_file?: string
}

export interface ParsedConfigTools {
  allowed?: string[]
  permission?: Record<string, any>
}

export interface AgentSkillRef {
  name: string
  source?: string
  inline?: string
  installed?: string
  when?: string[]
}

export interface SubagentConfig {
  name: string
  prompt?: {
    system?: string
    identity?: ParsedConfigPromptIdentity
  }
  tools?: ParsedConfigTools
  skills?: AgentSkillRef[]
}

export interface ParsedAgentConfig {
  prompt?: ParsedConfigPrompt
  tools?: ParsedConfigTools
  skills?: AgentSkillRef[]
  subagents?: SubagentConfig[]
}

export interface Agent {
  id: string
  agent_id: string
  name: string
  description: string | null
  version: string | null
  commit_id: string | null
  author: string | null
  source: string
  source_url: string
  category: string | null
  tags: string[] | null
  logo_url: string | null
  homepage_url: string | null
  license: string | null
  readme_content: string | null
  agent_yaml_content: string | null
  parsed_config: ParsedAgentConfig | null
  supported_platforms: string[] | null
  verified: boolean
  star_count: number
  contributor_count: number
  security_score: number | null
  download_count: number
  rating: string | null
  latest_commit_id: string | null
  created_at: string
  updated_at: string
}

export interface AgentVersion {
  version: string
  commit_id: string | null
  author: string | null
  message: string | null
  released_at: string | null
  download_count: number
}

export interface AgentListResponse {
  agents: Agent[]
  total: number
  skip: number
  limit: number
}

export interface AgentVersionsResponse {
  agent_id: string
  versions: AgentVersion[]
}