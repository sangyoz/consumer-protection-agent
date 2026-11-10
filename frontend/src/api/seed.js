export function seedCases() {
  const now = new Date().toISOString()
  return [
    { id: 'demo-fitness', title: '健身房停业，剩余会员费如何退还', summary: '购买了两年期健身会员卡，支付 3,600 元，使用约半年后门店停止营业。商家回复需要等待公司统一处理，希望退还未消费的费用。', merchant: '示例健身房', amount: 3600, goal: '核对剩余服务权益，协商退还未消费费用', stage: 'negotiating', createdAt: now, updatedAt: now, analysis: null, messages: [{ id: 'm1', role: 'merchant', content: '门店目前在调整经营，退款需要等公司统一处理，请您耐心等待。', createdAt: now }, { id: 'm2', role: 'assistant', content: '这条回复尚未明确处理期限。下一步可以要求商家说明退款方案、计算依据和完成时间。此处为演示建议。', createdAt: now }], materials: [{ id: 'e1', name: '会员合同.pdf', size: 128000, status: 'demo' }, { id: 'e2', name: '付款记录.png', size: 56000, status: 'demo' }], complaint: '', timeline: [{ id: 't1', text: '创建案件并整理会员合同与付款信息', createdAt: now }, { id: 't2', text: '进入沟通协商，等待明确退款方案', createdAt: now }] },
    { id: 'demo-shopping', title: '网购耳机出现质量问题，申请退货退款', summary: '收到耳机后发现右侧无法正常发声，已保留订单和问题视频，希望与商家协商退货退款。', merchant: '示例数码店', amount: 399, goal: '核对售后条件，申请退货退款', stage: 'collecting', createdAt: now, updatedAt: now, analysis: null, messages: [], materials: [], complaint: '', timeline: [{ id: 't3', text: '案件已创建，待补充订单及沟通记录', createdAt: now }] },
  ]
}
