<script setup>
import { computed } from 'vue'
import { useCasesStore } from '../../stores/cases'
import AppIcon from '../AppIcon.vue'
import GoalPlanPanel from './GoalPlanPanel.vue'
const props = defineProps({ item: Object })
const store = useCasesStore()
// 证据勾选后接口更新的是 item.evidence_checklist，分析结果里那份只作兜底。
const checklist = computed(() => (props.item.evidence_checklist?.length
  ? props.item.evidence_checklist
  : props.item.analysis?.evidence_checklist) || [])
async function analyze() { if (await store.act('analyze', props.item.id)) store.notify('分析已生成') }
async function updateEvidence(entry, event) {
  const status = event.target.checked ? 'user_confirmed' : 'missing'
  const result = await store.act('updateEvidence', props.item.id, { key: entry.key, status, note: '' })
  if (result) store.notify(event.target.checked ? '已记录你的证据自述' : '已更新证据状态')
}
</script>
<template>
  <div class="panel content-panel"><div class="panel-title"><h2>案件事实与初步分析</h2><span class="subtle-tag">{{ item.analysis ? (item.analysis.engine === 'deepseek' ? 'AI 分析' : '案情分析') : '等待梳理' }}</span></div><div class="fact-block"><span class="field-caption">你描述的情况</span><p>{{ item.summary }}</p></div><div class="fact-block"><span class="field-caption">当前诉求</span><p>{{ item.goal }}</p></div><GoalPlanPanel :item="item" /><template v-if="item.analysis"><div class="divider"></div><div class="panel-title"><h3>建议优先补充</h3><span class="small muted">结合本案信息生成</span></div><ul class="checklist"><li v-for="text in item.analysis.missing" :key="text"><AppIcon name="file" :size="16" />{{ text }}</li></ul><div v-if="checklist.length" class="evidence-checklist"><h3>证据链盘点</h3><label v-for="entry in checklist" :key="entry.key" class="check-row"><input type="checkbox" :checked="entry.status === 'user_confirmed' || entry.status === 'user_provided'" :disabled="store.busy || item.stage === 'resolved'" @change="updateEvidence(entry, $event)" /><span>{{ entry.item }}<small class="evidence-status">{{ entry.status === 'missing' ? '待补充' : entry.status === 'uploaded_unverified' ? '已上传，未核验' : '用户自述，未核验' }}</small></span></label></div><div class="law-card"><div class="panel-title"><h3>{{ item.analysis.legal.name }}</h3><span class="badge badge-collecting">{{ item.analysis.legal.verified ? '来源已匹配' : '待核验' }}</span></div><p>{{ item.analysis.legal.explanation }}</p><p v-for="citation in item.analysis.legal.citations || []" :key="citation.law_id"><strong>{{ citation.citation }}</strong><br />{{ citation.quote }}<br /><a :href="citation.source" target="_blank" rel="noopener noreferrer">查看官方来源</a></p></div><div class="fact-block"><span class="field-caption">诉求与依据</span><p>{{ item.analysis.rights }}</p><p>{{ item.analysis.strategy }}</p></div><details v-if="item.analysis.trace" class="audit-trace"><summary>本次处理记录</summary><p>节点：{{ item.analysis.trace.join(' → ') }}</p><p>法律来源与原文核验通过：{{ item.analysis.audit?.valid ? '是' : '否' }}；自动修正次数：{{ item.analysis.audit?.correction_attempts || 0 }}</p></details></template><div v-else class="inline-empty"><AppIcon name="chat" :size="25" /><p>先梳理已知事实，再核对证据和诉求。</p></div><div class="panel-actions"><button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved'" @click="analyze">{{ store.busy ? '正在处理…' : item.analysis ? '重新梳理案情' : '生成案情分析' }}</button><RouterLink :to="`/cases/${item.id}/negotiation`" class="btn btn-primary">进入沟通协商<AppIcon name="arrow" :size="16" /></RouterLink></div></div>
</template>
