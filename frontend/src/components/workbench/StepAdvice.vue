<script setup>
import { computed } from 'vue'
const props = defineProps({ item: Object, step: Object })
const guidance = {
  identity: ['核对经营主体', '对照订单、合同与实际收款方。名称不一致时，先保留记录并询问原因。'],
  evidence: ['整理证据后再推进', '勾选自己确实保存的证据；文件上传或用户确认都不代表内容已核验。'],
  calculation: ['核对退款计算依据', '均价计算只作估算。再核对已消费部分、优惠赠送与合同费用约定。'],
  platform: ['跟进平台处理', '记录平台实际答复；需要补充材料时先补齐，未解决时记录原因再评估下一步。'],
  complaint: ['核对投诉内容', '核对经营主体、诉求、时间和材料，确认后自行提交，并保存受理信息。'],
  authority: ['确认渠道能否受理', '先核对行业、属地与受理范围。暂不确定时记录咨询结果，避免重复提交。'],
  followup: ['核对实际履行', '记录处理期限、补材料要求和实际结果；退款到账或诉求落实后再确认结案。'],
  other: ['评估剩余路径', '结合已尝试方式和失败原因核对剩余渠道的条件、材料与成本。'],
  analysis: ['梳理事实和诉求', '先核对已知事实、现有证据和希望解决的问题，再决定后续安排。'],
}
const guide = computed(() => guidance[props.step?.type] || guidance.analysis)
const analysis = computed(() => props.item.analysis)
const showAnalysis = computed(() => ['analysis', 'evidence'].includes(props.step?.type) && analysis.value)
</script>
<template>
  <section class="right-advice stage-guide">
    <div class="panel-title"><h2>{{ guide[0] }}</h2></div>
    <p>{{ step?.reason || guide[1] }}</p>
    <p class="small muted">{{ guide[1] }}</p>
    <div v-if="step?.completion_condition" class="notice-box"><strong>完成条件</strong><p>{{ step.completion_condition }}</p></div>
    <template v-if="showAnalysis">
      <div class="advice-section"><h3>本轮分析建议</h3><p>{{ analysis.decision?.reason || analysis.strategy }}</p></div>
      <ul v-if="analysis.decision?.user_questions?.length" class="checklist"><li v-for="question in analysis.decision.user_questions" :key="question">{{ question }}</li></ul>
      <details class="advice-section"><summary>查看分析详情与法律来源</summary><p>{{ analysis.rights }}</p><p>{{ analysis.strategy }}</p><p>{{ analysis.legal?.explanation }}</p><p v-for="citation in analysis.legal?.citations || []" :key="citation.law_id"><strong>{{ citation.citation }}</strong><br />{{ citation.quote }}<br /><a :href="citation.source" target="_blank" rel="noopener noreferrer">查看官方来源</a></p><p class="fine-print">{{ analysis.legal?.verified ? '来源与原文已匹配，适用条件仍需核对。' : '法律依据待核对。' }}</p></details>
    </template>
  </section>
</template>
