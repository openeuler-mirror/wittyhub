import axios from 'axios'
import type { Skill, SkillListResponse, SearchResponse, SecurityAudit, DownloadResponse } from './types'

export interface SkillVersionsResponse {
  source_url: string
  skill_id: string
  versions: Skill[]
}

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

export interface Stats {
  total_skills: number
  total_categories: number
  categories: { name: string; count: number }[]
}

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
    mode?: 'text' | 'semantic' | 'hybrid'
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
  },

  async getStats(): Promise<Stats> {
    const { data } = await client.get('/index/stats')
    return data
  },

  async getCategories(): Promise<{ categories: { name: string; count: number }[] }> {
    const { data } = await client.get('/index/categories')
    return data
  }
}
