import axios from 'axios'
import type {
  Skill,
  SkillListResponse,
  SearchResponse,
  SecurityAudit,
  DownloadResponse,
  SkillVersionsResponse,
  Stats,
  Category
} from './types'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// Backend wraps every successful JSON response into
// { code, msg, data }. Unwrap it here so callers get the payload
// directly. Blob responses (file downloads) and error responses are untouched.
client.interceptors.response.use((response) => {
  if (response.config.responseType === 'blob') {
    return response
  }
  const body = response.data
  if (
    body &&
    typeof body === 'object' &&
    'code' in body &&
    'data' in body
  ) {
    response.data = body.data
  }
  return response
})

function parseContentDispositionFilename(header: string | undefined): string {
  if (!header) return 'skill.zip'
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match) {
    try { return decodeURIComponent(utf8Match[1].trim()) } catch { /* ignore */ }
  }
  const match = header.match(/filename="?([^";]+)"?/i)
  return match ? match[1].trim() : 'skill.zip'
}

export const api = {
  async listSkills(params: {
    skip?: number
    limit?: number
    category?: string
    platform?: string
    tags?: string
    security_level?: string
    sort_by?: 'updated_at' | 'download_count'
    sort_period?: 'week' | 'month'
  } = {}): Promise<SkillListResponse> {
    const { data } = await client.get('/skills/', { params })
    return data
  },

  async getSkill(skillId: string): Promise<Skill> {
    const { data } = await client.get(`/skills/${encodeURIComponent(skillId)}`)
    return data
  },

  async getSkillVersions(skillId: string): Promise<SkillVersionsResponse> {
    const { data } = await client.get(`/skills/versions/${encodeURIComponent(skillId)}`)
    return data
  },

  async searchSkills(params: {
    q?: string
    skip?: number
    limit?: number
    category?: string
    platform?: string
    tags?: string
    security_level?: string
    mode?: 'text' | 'semantic' | 'hybrid'
    scope?: 'summary' | 'full'
  } = {}): Promise<SearchResponse> {
    const { data } = await client.get('/index/search', { params })
    return data
  },

  async getSkillAudit(skillId: string): Promise<SecurityAudit | { error: string }> {
    const { data } = await client.get(`/skills/${encodeURIComponent(skillId)}/audit`)
    return data
  },

  async getSkillDownload(skillId: string): Promise<DownloadResponse> {
    const resp = await client.get(`/skills/${encodeURIComponent(skillId)}/download`, {
      responseType: 'blob'
    })
    const blob: Blob = resp.data
    const filename = parseContentDispositionFilename(resp.headers['content-disposition'])
    return { blob, filename }
  },

  async reindex(): Promise<{ status: string; indexed_count: number; total_skills: number }> {
    const { data } = await client.post('/index/reindex')
    return data
  },

  async getStats(): Promise<Stats> {
    const { data } = await client.get('/index/stats')
    return data
  },

  async getCategories(): Promise<{ categories: Category[] }> {
    const { data } = await client.get('/index/categories')
    return data
  }
}
