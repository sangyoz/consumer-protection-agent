// 仅用于页面联调的确定性模拟结果；真实能力在后端 services/ 中接入。
export function analyzeDemo(item) {
  return {
    summary: item.summary,
    category: /健身|会员|预付/.test(item.summary) ? '预付式消费纠纷' : '商品／服务消费纠纷',
    missing: ['核对商家名称与实际收款方', '补充合同、订单及付款凭证', '确认希望解决的问题和已沟通过程'],
    rights: '先核对交易事实、合同约定和证据，再确认可提出的退款、维修或履约诉求。当前内容仅用于展示分析页面。',
    legal: { name: '法律检索模块待接入', explanation: '正式接入后展示法律原文、通俗解释、适用条件和官方来源。当前没有已核验的法律结论。', source: '', verified: false },
    strategy: '先说明事实和具体诉求，要求商家明确答复处理方案与时间，保留沟通记录。',
    script: `您好，关于${item.title}，${item.goal}。请结合订单及实际履行情况，说明处理方案、计算依据和预计完成时间。`,
  }
}
export function replyDemo(content) {
  const concern = /等|通知|耐心/.test(content) ? '对方提到了等待，需要进一步明确处理期限。' : /不退|拒绝|规定/.test(content) ? '对方表达了拒绝处理的态度，需要核对具体理由和合同依据。' : '请核对对方是否明确回应了诉求、处理方式及完成时间。'
  return `${concern}建议保留本轮记录，并要求对方给出书面方案。这是模拟分析，不构成法律判断。`
}
export function complaintDemo(item) {
  return `【投诉材料草稿 · 待用户核对】\n\n投诉对象：${item.merchant || '待补充经营主体'}\n交易金额：${item.amount ? `${item.amount} 元` : '待补充'}\n\n纠纷经过：\n${item.summary}\n\n具体诉求：\n${item.goal}\n\n协商记录：\n${item.messages.filter(m => m.role === 'merchant').map(m => m.content).join('\n') || '待补充商家沟通记录'}\n\n证据清单：\n${item.materials.map(m => `· ${m.name}`).join('\n') || '待补充订单、付款凭证和相关材料'}\n\n法律依据：待检索并核验后补充。\n\n请核对真实事实、经营主体和附件，再选择适合的渠道提交。`
}
