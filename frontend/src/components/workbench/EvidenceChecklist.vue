<script setup>
import { computed } from 'vue'
import { useCasesStore } from '../../stores/cases'
const props = defineProps({ item: Object })
const store = useCasesStore()
const definitions = [
  ['transaction', '订单、合同或服务协议', true], ['payment', '付款凭证或交易记录', true],
  ['issue', '故障、停业或其他争议记录', false], ['communication', '与商家的沟通记录', false],
]
const labels = { missing: '尚未确认', uploaded_unverified: '文件已上传，内容未核验', user_confirmed: '你已确认掌握，内容未核验', user_provided: '你已提供相关记录，内容未核验', not_applicable: '暂不适用' }
const rows = computed(() => definitions.map(([key, label, required]) => ({
  key, item: label, required, status: 'missing',
  ...(props.item.evidence_checklist || []).find(row => row.key === key),
})))
async function confirm(row, checked) {
  if (await store.act('updateEvidence', props.item.id, { key: row.key, status: checked ? 'user_confirmed' : 'missing', note: row.note || '' })) {
    store.notify(checked ? '已记录你掌握这项证据，并重新评估后续步骤' : '已取消确认，并重新评估后续步骤')
  }
}
</script>
<template>
  <div class="evidence-checklist plan-step-body">
    <h3>确认你手上已有的材料</h3>
    <p class="small muted">即使暂不上传，也可以勾选自己已保存的材料。勾选只记录你的确认，不代表系统已审核文件。</p>
    <label v-for="row in rows" :key="row.key" class="check-row">
      <input type="checkbox" :checked="['user_confirmed', 'user_provided'].includes(row.status)" :disabled="store.busy || item.stage === 'resolved'" @change="confirm(row, $event.target.checked)" />
      <span>{{ row.item }}<small v-if="row.required"> · 核心材料</small><small class="evidence-status">{{ labels[row.status] || '待核对' }}</small></span>
    </label>
  </div>
</template>
