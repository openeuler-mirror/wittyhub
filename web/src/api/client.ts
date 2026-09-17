import axios from 'axios'
import type {
  Skill,
  SkillListResponse,
  SearchResponse,
  SecurityAudit,
  AuditReport,
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

  /** 风险评估报告：四大类 / 17 维度 / 检测项逐层聚合的完整报告（评分、等级、统计、命中项明细） */
  async getSkillAuditReport(skillId: string): Promise<AuditReport> {
    const { data } = await client.get(`/skills/${encodeURIComponent(skillId)}/audit-report`)
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
  },

  /** Fire-and-forget delivery for the analytics SDK's aggregated report.
   *
   * ``payload`` is the OpenEuler analytics envelope ``{ header, body: [...] }``
   * produced by the plugin and handed to our request callback; it is forwarded
   * verbatim to the shared openEuler data-collection endpoint (dsapi), mirroring
   * how openEuler-portal reports its own tracking events. See the reference at
   * tmp/openEuler-portal/app/.vitepress/src/api/api-analytics.ts.
   */
  async track(payload: Record<string, unknown>): Promise<void> {
    try {
      // Tag the collection-only envelope with our own value on the existing
      // `service` dimension (mirrors openEuler-portal's per-module $service).
      // This lets Grafana/other consumers tell wittyhub rows apart from the
      // openEuler portal data sharing the same dsapi endpoint, WITHOUT adding
      // handler-level events; per-event business dimensions (`module`, etc.)
      // stay untouched so they keep working as the primary filter too.
      const head = (payload.header ?? {}) as Record<string, unknown>
      const body = payload.body ?? []
      const tagged = {
        ...payload,
        header: { ...head, service: 'wittyhub' },
        body: Array.isArray(body)
          ? (body as Record<string, unknown>[]).map((ev) => {
              const props = ((ev as { properties?: object }).properties ?? {}) as Record<string, unknown>
              return { ...ev, properties: { ...props, service: 'wittyhub' } }
            })
          : body,
      }
      // Send on a fresh session (not the wrapped `client`) so the backend's
      // { code, msg, data } unwrap interceptor never interferes; this endpoint
      // is a third-party collector reached cross-origin.
      await axios.post('/api-dsapi/query/track/openeuler', tagged)
    } catch (e) {
      // Tracking must never break the user journey — swallow errors.
      console.error('Failed to report tracking event:', e)
    }
  }
}
