export const stages = { collecting: '待完善', analyzing: '分析中', negotiating: '协商中', complaining: '投诉中', following: '待履行', resolved: '已解决' }
export const steps = ['梳理案情', '明确诉求', '沟通协商', '准备投诉', '跟进结果']
export const stageStep = { collecting: 0, analyzing: 1, negotiating: 2, complaining: 3, following: 4, resolved: 5 }
export const sections = [{ key: 'analysis', label: '案件分析' }, { key: 'negotiation', label: '沟通协商' }, { key: 'complaint', label: '投诉准备' }, { key: 'other', label: '其他方案' }]
export const money = value => Number(value || 0).toLocaleString('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 2 })
export const shortDate = value => new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })

export function createCase(input) {
  const now = new Date().toISOString()
  return { id: globalThis.crypto.randomUUID(), title: input.title || '新建消费纠纷', summary: input.summary, merchant: input.merchant || '', amount: Number(input.amount || 0), goal: input.goal || '希望协助梳理合理诉求', stage: 'collecting', createdAt: now, updatedAt: now, analysis: null, messages: [], materials: input.materials || [], complaint: '', timeline: [{ id: globalThis.crypto.randomUUID(), text: '案件已创建，等待补充信息', createdAt: now }] }
}
