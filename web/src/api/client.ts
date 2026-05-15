import axios from 'axios'
import type { Skill, SkillListResponse, SearchResponse, SecurityAudit, DownloadResponse } from './types'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

export const api = {
  async listSkills(params: {
    skip?: number
    limit?: number
    category?: string
    platform?: string
    tags?: string
  } = {}): Promise<SkillListResponse> {
    const { data } = await client.get('/skills/', { params })
    return data
  },

  async getSkill(skillId: string): Promise<Skill> {
    const { data } = await client.get(`/skills/${encodeURIComponent(skillId)}`)
    return data
  },

  async searchSkills(params: {
    q?: string
    skip?: number
    limit?: number
    category?: string
    platform?: string
    tags?: string
  } = {}): Promise<SearchResponse> {
    const { data } = await client.get('/index/search', { params })
    return data
  },

  async getSkillAudit(skillId: string): Promise<SecurityAudit | { error: string }> {
    const { data } = await client.get(`/skills/${encodeURIComponent(skillId)}/audit`)
    return data
  },

  async getSkillDownload(skillId: string): Promise<DownloadResponse> {
    const { data } = await client.get(`/skills/${encodeURIComponent(skillId)}/download`)
    return data
  },

  async reindex(): Promise<{ status: string; indexed_count: number; total_skills: number }> {
    const { data } = await client.post('/index/reindex')
    return data
  }
}