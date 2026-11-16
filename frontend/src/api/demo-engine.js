// 仅用于页面联调的确定性模拟结果；真实能力在后端 services/ 中接入。
const EVIDENCE_DEFS = [
  ['transaction', '订单、合同或服务协议', ['订单', '合同', 'order', 'contract'], true],
  ['payment', '付款凭证或交易记录', ['付款', '支付', '收据', 'payment', 'receipt'], true],
  ['issue', '与争议对应的问题记录或服务履约记录', ['照片', '视频', '检测', '停业', 'photo', 'video'], false],
  ['communication', '与商家的沟通记录', ['聊天', '沟通', 'chat'], false],
]

function evidenceChecklist(item) {
  return EVIDENCE_DEFS.map(([key, label, hints, required]) => {
    const materials = (item.materials || []).filter(material =>
      hints.some(hint => (material.name || '').toLowerCase().includes(hint))
    )
    let status = materials.length ? 'uploaded_unverified' : 'missing'
    if (key === 'communication' && (item.messages || []).some(message => message.role === 'merchant')) {
      status = 'user_provided'
    }
    return {
      key,
      item: label,
      status,
      material_ids: materials.map(material => material.id),
      note: '',
      required,
      content_verified: false,
    }
  })
}

export function analyzeDemo(item) {
  const checklist = evidenceChecklist(item)
  const needsEvidence = checklist.some(row => row.required && row.status === 'missing')
  const action = needsEvidence ? 'collect_evidence' : 'negotiate'
  return {
    summary: item.summary,
    category: /健身|会员|预付/.test(item.summary) ? '预付式消费纠纷' : '商品／服务消费纠纷',
    missing: checklist.filter(row => row.status === 'missing').map(row => row.item),
    rights: '先核对交易事实、合同约定和证据，再确认可提出的退款、维修或履约诉求。当前内容仅用于展示分析页面。',
    legal: {
      name: '法律检索模块待接入',
      explanation: '正式接入后展示法律原文、通俗解释、适用条件和官方来源。当前没有已核验的法律结论。',
      source: '',
      verified: false,
      citations: [],
    },
    strategy: '先说明事实和具体诉求，要求商家明确答复处理方案与时间，保留沟通记录。',
    script: `您好，关于${item.title}，${item.goal}。请结合订单及实际履行情况，说明处理方案、计算依据和预计完成时间。`,
    evidence_checklist: checklist,
    engine: 'demo',
    decision: { action, reason: needsEvidence ? '优先补齐核心交易证据' : '结合已有事实继续协商', tools: [], query: '' },
    retrieval: { law_library: 'not_requested', law_search_mode: 'none', case_search: 'not_requested' },
    audit: { valid: true, invalid_citations: [], used_law_ids: [], scope: 'demo', correction_attempts: 0 },
    merchant_claim_checks: [],
    retrieved_cases: [],
    trace: ['assess_evidence', 'decide', action, 'audit_citations', 'finish'],
  }
}
export function replyDemo(content) {
  const concern = /等|通知|耐心/.test(content) ? '对方提到了等待，需要进一步明确处理期限。' : /不退|拒绝|规定/.test(content) ? '对方表达了拒绝处理的态度，需要核对具体理由和合同依据。' : '请核对对方是否明确回应了诉求、处理方式及完成时间。'
  return `${concern}建议保留本轮记录，并要求对方给出书面方案。这是模拟分析，不构成法律判断。`
}
export function complaintDemo(item) {
  return `【投诉材料草稿 · 待用户核对】\n\n投诉对象：${item.merchant || '待补充经营主体'}\n交易金额：${item.amount ? `${item.amount} 元` : '待补充'}\n\n纠纷经过：\n${item.summary}\n\n具体诉求：\n${item.goal}\n\n协商记录：\n${item.messages.filter(m => m.role === 'merchant').map(m => m.content).join('\n') || '待补充商家沟通记录'}\n\n证据清单：\n${item.materials.map(m => `· ${m.name}`).join('\n') || '待补充订单、付款凭证和相关材料'}\n\n法律依据：待检索并核验后补充。\n\n请核对真实事实、经营主体和附件，再选择适合的渠道提交。`
}
