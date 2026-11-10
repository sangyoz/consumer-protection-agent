<script setup>
import { useCasesStore } from '../../stores/cases'
import AppIcon from '../AppIcon.vue'
const props = defineProps({ item: Object })
const store = useCasesStore()
async function analyze() { if (await store.act('analyze', props.item.id)) store.notify('演示分析已生成，法律依据仍待核验') }
</script>
<template>
  <div class="panel content-panel"><div class="panel-title"><h2>案件事实与初步分析</h2><span class="subtle-tag">{{ item.analysis ? '模拟分析' : '等待梳理' }}</span></div><div class="fact-block"><span class="field-caption">你描述的情况</span><p>{{ item.summary }}</p></div><div class="fact-block"><span class="field-caption">当前诉求</span><p>{{ item.goal }}</p></div><template v-if="item.analysis"><div class="divider"></div><div class="panel-title"><h3>建议优先补充</h3><span class="small muted">由演示规则生成</span></div><ul class="checklist"><li v-for="text in item.analysis.missing" :key="text"><AppIcon name="file" :size="16" />{{ text }}</li></ul><div class="law-card"><div class="panel-title"><h3>{{ item.analysis.legal.name }}</h3><span class="badge badge-collecting">待核验</span></div><p>{{ item.analysis.legal.explanation }}</p></div><div class="fact-block"><span class="field-caption">诉求与依据</span><p>{{ item.analysis.rights }}</p></div></template><div v-else class="inline-empty"><AppIcon name="chat" :size="25" /><p>先梳理已知事实，再核对证据和诉求。</p><span class="small muted">当前使用模拟结果，供后续接入 Agent。</span></div><div class="panel-actions"><button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved'" @click="analyze">{{ store.busy ? '正在处理…' : item.analysis ? '重新梳理案情' : '生成案情分析' }}</button><RouterLink :to="`/cases/${item.id}/negotiation`" class="btn btn-primary">进入沟通协商<AppIcon name="arrow" :size="16" /></RouterLink></div></div>
</template>
