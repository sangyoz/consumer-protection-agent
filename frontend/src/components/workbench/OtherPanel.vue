<script setup>
import { computed, ref } from 'vue'
import { useCasesStore } from '../../stores/cases'
import ProgressRecordForm from './ProgressRecordForm.vue'
const props = defineProps({ item: Object })
const store = useCasesStore()
const attempts = computed(() => (props.item.plan?.steps || []).filter(row => ['completed', 'failed', 'skipped'].includes(row.status)))
const alternatives = computed(() => props.item.plan?.alternatives || [])
const selectedChannel = ref('')
async function refresh() {
  if (await store.act('replan', props.item.id)) store.notify('已更新剩余办法建议，案件步骤保持不变')
}
</script>

<template>
  <section class="panel content-panel">
    <div class="panel-title"><h2>其他维权方式</h2><span class="subtle-tag">结合本案重新评估</span></div>
    <p class="body-copy muted">如果前面的方式没有解决问题，补充失败原因和新反馈后，再判断还有哪些办法可尝试。案件已解决时无需执行本步骤。</p>
    <div class="fact-block plan-step-body"><span class="field-caption">已有处理记录</span><ul v-if="attempts.length" class="checklist"><li v-for="step in attempts" :key="step.id">{{ step.title }}：{{ step.note || '已记录结果' }}</li></ul><p v-else class="small muted">还没有记录步骤结果。可在本页下方补充已尝试的方式，或返回对应步骤记录结果。</p></div>
    <button class="btn btn-primary" :disabled="store.busy || item.stage === 'resolved'" @click="refresh">{{ store.busy ? '正在评估…' : '重新评估剩余办法' }}</button>
    <div v-if="alternatives.length" class="channel-grid plan-step-body"><article v-for="entry in alternatives" :key="entry.channel" class="channel-card"><h3>{{ entry.title }}</h3><p>{{ entry.reason }}</p><div class="notice-box"><strong>先核对适用条件</strong><p>{{ entry.conditions }}</p></div><p class="small muted">准备材料：{{ entry.materials.join('、') }}</p><button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved'" @click="selectedChannel = entry.channel">{{ selectedChannel === entry.channel ? '已选中，在下方记录反馈' : '记录此渠道的反馈' }}</button></article></div>
    <div v-else class="inline-empty"><p>{{ (item.plan?.alternatives_engine || item.plan?.engine) === 'rules' ? '当前为规则初步规划，尚无针对本案的 AI 替代路径评估。' : '当前没有足够依据推荐新的渠道，请补充已尝试的方式、失败原因和经营主体信息。' }}</p></div>
    <p class="fine-print">以上为待核对的路径建议，不代表一定受理或成功；涉及仲裁、诉讼时应进一步核对管辖、期限、费用与证据条件。</p>
    <RouterLink :to="{ path: '/follow-up', query: { case: item.id } }" class="text-link">补充处理反馈或确认结案</RouterLink>
    <ProgressRecordForm :item="item" :channel="selectedChannel" title="补充已尝试方式与失败原因" />
  </section>
</template>
