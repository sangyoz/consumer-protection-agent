export const stages = { collecting: '待完善', analyzing: '分析中', negotiating: '协商中', complaining: '投诉中', following: '待履行', resolved: '已解决' }
export const steps = ['梳理案情', '明确诉求', '沟通协商', '准备投诉', '跟进结果']
export const stageStep = { collecting: 0, analyzing: 1, negotiating: 2, complaining: 3, following: 4, resolved: 5 }
export const sections = [{ key: 'analysis', label: '案件分析' }, { key: 'negotiation', label: '沟通协商' }, { key: 'complaint', label: '投诉准备' }, { key: 'other', label: '其他方案' }]

export const MATERIAL_KINDS = { order: '订单/付款凭证', contract: '合同/宣传页', photo: '问题照片/视频', chat: '沟通记录', other: '其他材料' }
export const MATERIAL_SOURCES = { user: '用户上传', extracted: '文件提取', inferred: 'AI 推断' }
export const REQUIRED_MATERIALS = [
  { kind: 'order', label: '订单或付款凭证' },
  { kind: 'photo', label: '问题照片或视频' },
  { kind: 'chat', label: '与商家沟通记录' },
]

export const CHANNELS = [
  { key: 'platform', name: '交易平台售后', category: '商业平台投诉', scope: '网购订单优先在平台内申请售后或平台介入，处理速度通常较快。', materials: ['order', 'chat'] },
  { key: 'market_12315', name: '12315 平台 / 市场监管部门', category: '行政投诉', scope: '商家拒绝处理、拖延推诿或涉嫌违法违规时，向市场监管部门投诉。', materials: ['order', 'photo', 'chat'] },
  { key: 'hotline_12345', name: '12345 政务服务便民热线', category: '行政投诉', scope: '需要协调属地部门处理、或不清楚对应监管部门时拨打。', materials: ['order'] },
  { key: 'consumer_assoc', name: '消费者协会调解', category: '调解渠道', scope: '自愿向消协申请调解，适合希望第三方居中协商的纠纷。', materials: ['order', 'chat'] },
  { key: 'industry', name: '行业主管部门', category: '行政投诉', scope: '食品、预付卡、服务等特定行业，向对应行业监管部门反映。', materials: ['order', 'contract'] },
  { key: 'justice', name: '仲裁或人民法院', category: '司法救济', scope: '争议较大、金额较高，或其他渠道无果后的司法途径。', materials: ['order', 'contract', 'chat'] },
]

export const ACCEPT_STATUSES = { pending: '待受理', accepted: '已受理', supplement: '需补充材料', rejected: '未受理', contacted: '商家已联系', resolved: '已履行' }

export const money = value => Number(value || 0).toLocaleString('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 2 })
export const shortDate = value => new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })

const IMAGE_SUFFIXES = ['.png', '.jpg', '.jpeg']

export function kindFromName(name) {
  const normalized = (name || '').toLowerCase()
  const suffix = normalized.slice(normalized.lastIndexOf('.'))
  return IMAGE_SUFFIXES.includes(suffix) ? 'photo' : 'other'
}

export function missingMaterials(materials) {
  const uploaded = new Set((materials || []).map(m => m.kind))
  return REQUIRED_MATERIALS.filter(item => !uploaded.has(item.kind))
}

/** 未填标题时用"诉求 · 商品"拼一个能认出来的标题，便于列表扫读。 */
export function defaultTitle(input) {
  return [input.goal, input.product]
    .map(value => String(value || '').trim())
    .filter(Boolean)
    .join(' · ')
}

export function createCase(input) {
  const now = new Date().toISOString()
  return {
    id: globalThis.crypto.randomUUID(),
    title: input.title || defaultTitle(input) || '新建消费纠纷',
    summary: input.summary,
    merchant: input.merchant || '',
    amount: Number(input.amount || 0),
    goal: input.goal || '希望协助梳理合理诉求',
    tradeTime: input.tradeTime || '',
    platform: input.platform || '',
    product: input.product || '',
    payee: input.payee || '',
    creditCode: input.creditCode || '',
    stage: 'collecting',
    createdAt: now,
    updatedAt: now,
    analysis: null,
    messages: [],
    materials: input.materials || [],
    complaint: '',
    complaintAttachments: [],
    goalPlan: null,
    resolution: null,
    followups: [],
    timeline: [{ id: globalThis.crypto.randomUUID(), text: '案件已创建，等待补充信息', createdAt: now }],
  }
}
