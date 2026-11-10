import axios from 'axios'
import { createCase } from '../domain/case'
import { seedCases } from './seed'
import { analyzeDemo, replyDemo, complaintDemo } from './demo-engine'

export const dataMode = import.meta.env.VITE_DATA_MODE === 'api' ? 'api' : 'mock'
const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api', timeout: 30000 })
const storageKey = 'youli.cases.v1'
let memory = null
function read() {
  if (memory) return structuredClone(memory)
  try { memory = JSON.parse(localStorage.getItem(storageKey) || 'null') } catch { /* 损坏的本地数据恢复为演示数据 */ }
  if (!Array.isArray(memory)) memory = seedCases()
  return structuredClone(memory)
}
function write(items) {
  memory = structuredClone(items)
  try { localStorage.setItem(storageKey, JSON.stringify(items)) } catch { /* 存储受限时保留当前会话 */ }
}
function mutate(id, action) {
  const items = read()
  const item = items.find(c => c.id === id)
  if (!item) throw new Error('案件不存在，请返回案件中心。')
  action(item)
  item.updatedAt = new Date().toISOString()
  write(items)
  return item
}
function event(item, text) { item.timeline.push({ id: crypto.randomUUID(), text, createdAt: new Date().toISOString() }) }
function ensureOpen(item) { if (item.stage === 'resolved') throw new Error('案件已解决，请先在处理跟进中更新状态。') }
const mock = {
  async listCases() { return read().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)) },
  async getCase(id) { const item = read().find(c => c.id === id); if (!item) throw new Error('案件不存在，请返回案件中心。'); return item },
  async createCase(input) { const item = createCase(input); write([item, ...read()]); return item },
  async analyze(id) { return mutate(id, item => { ensureOpen(item); item.analysis = analyzeDemo(item); if (item.stage === 'collecting') item.stage = 'analyzing'; event(item, '已生成演示案情分析，法律依据待核验') }) },
  async sendMessage(id, content) { return mutate(id, item => { ensureOpen(item); const createdAt = new Date().toISOString(); item.messages.push({ id: crypto.randomUUID(), role: 'merchant', content, createdAt }, { id: crypto.randomUUID(), role: 'assistant', content: replyDemo(content), createdAt }); item.stage = 'negotiating'; event(item, '记录商家回复并生成演示沟通建议') }) },
  async generateComplaint(id) { return mutate(id, item => { ensureOpen(item); item.complaint = complaintDemo(item); item.stage = 'complaining'; event(item, '生成投诉草稿，尚未向任何平台提交') }) },
  async addMaterials(id, files) { return mutate(id, item => { ensureOpen(item); item.materials.push(...files.map(file => ({ id: crypto.randomUUID(), name: file.name, size: file.size, status: 'metadata' }))); event(item, '记录附件名称；本地演示不保存文件内容') }) },
  async updateProgress(id, payload) { return mutate(id, item => { if (payload.stage === 'resolved' && !payload.confirmed) throw new Error('请先确认诉求已实际履行。'); if (payload.stage) item.stage = payload.stage; event(item, payload.note) }) },
}
const real = {
  async listCases() { return (await http.get('/cases')).data },
  async getCase(id) { return (await http.get(`/cases/${id}`)).data },
  async createCase(input) { return (await http.post('/cases', input)).data },
  async analyze(id) { return (await http.post(`/cases/${id}/analysis`)).data },
  async sendMessage(id, content) { return (await http.post(`/cases/${id}/messages`, { content })).data },
  async generateComplaint(id) { return (await http.post(`/cases/${id}/complaint`)).data },
  async addMaterials(id, files) { const data = new FormData(); files.forEach(file => data.append('files', file)); return (await http.post(`/cases/${id}/materials`, data)).data },
  async updateProgress(id, payload) { return (await http.post(`/cases/${id}/progress`, payload)).data },
}
export const api = dataMode === 'mock' ? mock : real
