<script setup>
import { computed, ref } from 'vue'
import { useCasesStore } from '../../stores/cases'
import AppIcon from '../AppIcon.vue'
const props = defineProps({ item: Object })
const store = useCasesStore()
const tone = ref('理性坚定')
const script = computed(() => {
  const generated = props.item.analysis?.script
  if (generated) return `${tone.value === '温和协商' ? '您好，希望能一起妥善解决这个问题。' : tone.value === '正式严肃' ? '请贵方对以下事项提供明确的书面答复。' : ''}${generated}`
  return `${tone.value === '温和协商' ? '您好，希望能一起妥善解决这个问题。' : tone.value === '正式严肃' ? '请贵方对以下事项提供明确的书面答复。' : '您好，我希望就目前的问题明确一个处理方案。'}${props.item.goal}。请说明处理方式、计算依据和预计完成时间。`
})
async function copy() { try { await navigator.clipboard.writeText(script.value); store.notify('话术已复制，请核对后自行发送') } catch { store.notify('复制失败，请手动选择话术文本') } }
</script>

<template>
  <section class="right-advice"><div class="panel-title"><h2>本轮沟通建议</h2><span class="small muted">待你确认</span></div><div class="strategy-card"><h3>当前策略：{{ ({ collect_evidence: '优先补充证据', negotiate: '继续沟通协商', escalate: '评估升级处理', complaint: '准备投诉材料' })[item.analysis?.decision?.action] || '要求明确处理方案' }}</h3><p>{{ item.analysis?.strategy || '先核对事实和诉求，询问商家处理方案与明确期限，并保留沟通记录。' }}</p></div><div class="advice-section"><h3>法律依据</h3><details class="law-card"><summary>查看依据与适用条件</summary><p>{{ item.analysis?.legal.explanation || '尚无已核验法条引用。' }}</p><span class="badge badge-collecting">{{ item.analysis?.legal.verified ? '来源已匹配，适用条件待核对' : '待核验' }}</span></details></div><div class="advice-section"><div class="panel-title"><h3>建议发送的话术</h3><select v-model="tone" aria-label="话术语气"><option>理性坚定</option><option>温和协商</option><option>正式严肃</option></select></div><div class="script-box">{{ script }}</div><button class="btn btn-secondary copy-btn" @click="copy"><AppIcon name="copy" :size="15" />复制话术</button></div><p class="fine-print">核对事实与诉求后自行发送；模型建议和证据内容仍需你核对。</p></section>
</template>
