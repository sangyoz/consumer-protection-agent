import axios from 'axios'
import { createCase, kindFromName } from '../domain/case'
import { extractFields } from '../domain/extract'
import { seedCases } from './seed'
import { analyzeDemo, replyDemo, complaintDemo } from './demo-engine'

export const dataMode = import.meta.env.VITE_DATA_MODE === 'api' ? 'api' : 'mock'
const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api', timeout: 180000 })
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
  async updateCase(id, payload) { return mutate(id, item => { ensureOpen(item); Object.assign(item, payload); if (!item.title) item.title = item.summary.slice(0, 24); event(item, '已更新案件基本信息') }) },
  async analyze(id) { return mutate(id, item => { ensureOpen(item); item.analysis = analyzeDemo(item); if (item.stage === 'collecting') item.stage = 'analyzing'; event(item, '已生成演示案情分析，法律依据待核验') }) },
  async sendMessage(id, content) { return mutate(id, item => { ensureOpen(item); const createdAt = new Date().toISOString(); item.messages.push({ id: crypto.randomUUID(), role: 'merchant', content, createdAt }, { id: crypto.randomUUID(), role: 'assistant', content: replyDemo(content), createdAt }); item.stage = 'negotiating'; event(item, '记录商家回复并生成演示沟通建议') }) },
  async generateComplaint(id) { return mutate(id, item => { ensureOpen(item); item.complaint = complaintDemo(item); item.stage = 'complaining'; event(item, '生成投诉草稿，尚未向任何平台提交') }) },
  async addMaterials(id, files) { return mutate(id, item => { ensureOpen(item); item.materials.push(...files.map(file => ({ id: crypto.randomUUID(), name: file.name, size: file.size, status: 'metadata', kind: kindFromName(file.name), source: 'user', uploadedAt: new Date().toISOString() }))); event(item, '记录附件名称；本地演示不保存文件内容') }) },
  async deleteMaterial(id, materialId) { return mutate(id, item => { ensureOpen(item); const index = item.materials.findIndex(m => m.id === materialId); if (index < 0) throw new Error('材料不存在。'); const [removed] = item.materials.splice(index, 1); event(item, `已删除材料 ${removed.name}`) }) },
  async updateMaterialKind(id, materialId, kind) { return mutate(id, item => { ensureOpen(item); const material = item.materials.find(m => m.id === materialId); if (!material) throw new Error('材料不存在。'); material.kind = kind; event(item, `已更新材料「${material.name}」的类型`) }) },
  async downloadMaterial() { throw new Error('演示模式只记录文件名，没有可下载的文件。') },
  async updateProgress(id, payload) { return mutate(id, item => { if (payload.stage === 'resolved' && !payload.confirmed) throw new Error('请先确认诉求已实际履行。'); if (payload.stage) item.stage = payload.stage; const followup = { id: crypto.randomUUID(), note: payload.note, stage: payload.stage || null, confirmed: payload.confirmed, channel: payload.channel || null, caseNo: payload.caseNo || null, acceptStatus: payload.acceptStatus || null, deadline: payload.deadline || null, createdAt: new Date().toISOString() }; item.followups = item.followups || []; item.followups.push(followup); let detail = payload.note; if (followup.channel) detail += `（渠道：${followup.channel}）`; if (followup.caseNo) detail += `（编号：${followup.caseNo}）`; event(item, detail) }) },
  async deleteCase(id) { const items = read(); const index = items.findIndex(c => c.id === id); if (index < 0) throw new Error('案件不存在，请返回案件中心。'); items.splice(index, 1); write(items); return { ok: true, id } },
  async extract(text) { return extractFields(text) },
  async updateEvidence(id, payload) { return mutate(id, item => { ensureOpen(item); item.evidence_checklist ||= []; const source = item.analysis?.evidence_checklist || []; const index = item.evidence_checklist.findIndex(row => row.key === payload.key); const base = item.evidence_checklist[index] || source.find(row => row.key === payload.key) || { key: payload.key }; const row = { ...base, key: payload.key, status: payload.status, note: payload.note || '', content_verified: false }; if (index < 0) item.evidence_checklist.push(row); else item.evidence_checklist[index] = row; event(item, '更新用户自述证据状态；附件内容尚未核验') }) },
}
const real = {
  async listCases() { return (await http.get('/cases')).data },
  async getCase(id) { return (await http.get(`/cases/${id}`)).data },
  async createCase(input) { return (await http.post('/cases', input)).data },
  async updateCase(id, payload) { return (await http.put(`/cases/${id}`, payload)).data },
  async analyze(id) { return (await http.post(`/cases/${id}/analysis`)).data },
  async sendMessage(id, content) { return (await http.post(`/cases/${id}/messages`, { content })).data },
  async generateComplaint(id) { return (await http.post(`/cases/${id}/complaint`)).data },
  async addMaterials(id, files) { const data = new FormData(); files.forEach(file => data.append('files', file)); return (await http.post(`/cases/${id}/materials`, data)).data },
  async deleteMaterial(id, materialId) { return (await http.delete(`/cases/${id}/materials/${materialId}`)).data },
  async updateMaterialKind(id, materialId, kind) { return (await http.patch(`/cases/${id}/materials/${materialId}`, { kind })).data },
  async downloadMaterial(id, materialId) { const response = await http.get(`/cases/${id}/materials/${materialId}/download`, { responseType: 'blob' }); return response.data },
  async updateProgress(id, payload) { return (await http.post(`/cases/${id}/progress`, payload)).data },
  async deleteCase(id) { return (await http.delete(`/cases/${id}`)).data },
  async extract(text) { return (await http.post('/extract', { text })).data },
  async updateEvidence(id, payload) { return (await http.post(`/cases/${id}/evidence`, payload)).data },
}
export const api = dataMode === 'mock' ? mock : real
