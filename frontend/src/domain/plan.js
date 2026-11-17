export const STEP_TYPES = {
  analysis: ['案件分析', '核对事实和当前诉求'],
  identity: ['经营主体核对', '核对合同、订单与实际收款方'],
  evidence: ['补充证据', '补充交易、付款与问题记录'],
  calculation: ['退款金额核算', '核对已付、已消费与剩余金额'],
  negotiation: ['沟通协商', '提出具体诉求并记录商家书面回复'],
  platform: ['交易平台介入', '核对平台订单、售后规则与申诉条件'],
  complaint: ['投诉材料准备', '整理待核对的投诉草稿'],
  authority: ['主管渠道核对', '核对行业、属地与受理范围'],
  followup: ['处理跟进', '记录受理结果、期限与实际履行'],
  other: ['其他维权方式', '结合前面尝试，评估剩余可行路径'],
}
export const TERMINAL_STEPS = ['completed', 'failed', 'skipped']
export const STEP_STATUS = { active: '当前建议', pending: '待处理', completed: '已完成', failed: '未解决', skipped: '不适用' }

export function rulePlan(item, trigger = 'initial') {
  const text = `${item.summary || ''} ${item.product || ''}`
  const types = []
  const failed = new Set((item.plan?.steps || []).filter(row => row.status === 'failed').map(row => row.type))
  if (!item.merchant) types.push('identity')
  if (!['transaction', 'payment'].every(key => item.evidence_checklist?.some(row => row.key === key && ['user_confirmed', 'user_provided'].includes(row.status)))) types.push('evidence')
  if (/预付|会员|健身|未消费|剩余/.test(text)) types.push('calculation')
  if (failed.has('complaint')) types.push('authority', 'followup')
  else if (failed.has('negotiation') || failed.has('platform') || /拒绝|协商无果|协商失败|一直不退|多次联系无果/.test(text)) types.push('complaint', 'followup')
  else {
    types.push('negotiation')
    if (item.platform && !['线下门店', '实体店', '超市', '商场'].includes(item.platform)) types.push('platform')
  }
  const old = item.plan || {}
  if (trigger === 'case_updated' && old.steps?.some(row => row.type === 'evidence' && row.status === 'active') && !types.includes('evidence')) types.unshift('evidence')
  const frozen = (old.steps || []).filter(row => TERMINAL_STEPS.includes(row.status) && row.type !== 'other')
  const seen = new Set(frozen.map(row => row.type))
  const steps = [...structuredClone(frozen), ...[...new Set(types)].filter(type => !seen.has(type)).map(type => ({
    id: type, type, title: STEP_TYPES[type][0], reason: STEP_TYPES[type][1], status: 'pending',
    completion_condition: '记录实际处理结果后，由你确认完成、失败或不适用',
  })), { id: 'other', type: 'other', title: STEP_TYPES.other[0], reason: STEP_TYPES.other[1], status: 'pending' }]
  const active = steps.find(row => !TERMINAL_STEPS.includes(row.status))
  active.status = 'active'
  return { version: (old.version || 0) + 1, current_step_id: active.id, steps, engine: 'rules', trigger,
    reason: '按已填写事实生成初步路径，收到反馈后重新调整。演示模式使用本地规则。',
    alternatives: [], updated_at: new Date().toISOString() }
}

export function caseSteps(item) {
  return (item?.plan || rulePlan(item || {})).steps.map(row => ({ ...row, key: row.id, label: row.title }))
}

export function refreshMockPlan(item, trigger) {
  if (item.stage === 'resolved') return
  if (item.plan) item.plan_history = [...(item.plan_history || []), structuredClone(item.plan)].slice(-10)
  item.plan = rulePlan(item, trigger)
}
