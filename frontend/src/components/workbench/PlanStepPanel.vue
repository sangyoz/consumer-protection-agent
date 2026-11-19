<script setup>
import { reactive, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import GoalPlanPanel from './GoalPlanPanel.vue'
import MaterialList from './MaterialList.vue'
import EvidenceChecklist from './EvidenceChecklist.vue'
import ProgressRecordForm from './ProgressRecordForm.vue'
import RefundCalculator from './RefundCalculator.vue'
import { dataMode } from '../../api'
const props = defineProps({ item: Object, step: Object })
const store = useCasesStore()
const introductions = {
  identity: '填写订单或合同上的经营者信息。', evidence: '上传材料，或勾选你已经保存在手上的证据。',
  calculation: '填写实付金额和使用情况，估算后保存到诉求草稿。', platform: '把平台的实际答复和当前处理状态记在这里。',
  authority: '记录已咨询的渠道、受理条件与答复。', followup: '补充最新进展、处理期限和实际履行情况。',
}
const identity = reactive({ merchant: '', payee: '', creditCode: '' })
watch(() => props.item.id, () => Object.keys(identity).forEach(key => { identity[key] = props.item[key] || '' }), { immediate: true })
async function saveIdentity() {
  if (!identity.merchant.trim()) { store.notify('请填写订单或合同上的经营者名称，暂不清楚可在步骤结果中说明'); return }
  if (await store.act('updateCase', props.item.id, { merchant: identity.merchant.trim(), payee: identity.payee.trim(), creditCode: identity.creditCode.trim() })) store.notify('主体信息已保存')
}
async function upload(event) {
  const files = [...event.target.files]; event.target.value = ''
  if (!files.length) return
  if (files.length > 5 || files.some(file => !/\.(pdf|docx|png|jpe?g|txt)$/i.test(file.name) || file.size > 10 * 1024 * 1024 || !file.size)) { store.notify('每次最多5份非空文件，单份不超过10 MB，支持PDF、DOCX、图片和TXT'); return }
  if (await store.act('addMaterials', props.item.id, files)) store.notify(dataMode === 'mock' ? '演示模式仅记录文件名，未保存文件内容' : '材料已上传，文件内容仍待核验')
}
async function analyze() {
  if (await store.act('analyze', props.item.id)) store.notify('已生成分析，请查看右侧本轮建议')
}
</script>

<template>
  <section class="panel content-panel">
    <div class="panel-title"><h2>{{ step.title }}</h2><span class="subtle-tag">本案处理步骤</span></div>
    <p class="body-copy muted">{{ introductions[step.type] }}</p>
    <div v-if="step.type === 'calculation'" class="plan-step-body"><RefundCalculator :item="item" /><details class="plan-step-body"><summary>编辑完整诉求与计算依据</summary><GoalPlanPanel :item="item" /></details></div>
    <form v-if="step.type === 'identity'" @submit.prevent="saveIdentity"><fieldset class="step-fieldset" :disabled="store.busy || item.stage === 'resolved'"><label class="field">订单或合同上的经营者名称<input v-model="identity.merchant" maxlength="200" required placeholder="请按订单或合同原文填写" /></label><label class="field">实际收款方（选填）<input v-model="identity.payee" maxlength="200" /></label><label class="field">统一社会信用代码（选填）<input v-model="identity.creditCode" maxlength="30" pattern="[A-Za-z0-9 ]*" /></label><button class="btn btn-primary" type="submit">保存主体信息</button></fieldset></form>
    <template v-if="step.type === 'evidence'">
      <label class="upload-btn evidence-upload" :class="{ disabled: store.busy || item.stage === 'resolved' }">{{ store.busy ? '正在保存…' : '上传证据材料' }}<input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg,.txt" multiple :disabled="store.busy || item.stage === 'resolved'" @change="upload" /></label>
      <p class="fine-print">每次最多5份，单份不超过10 MB。支持PDF、DOCX、图片和TXT；视频请先自行保存，可上传关键截图。</p>
      <EvidenceChecklist :item="item" />
      <details class="plan-step-body"><summary>已上传材料（{{ item.materials.length }}份）</summary><MaterialList :item="item" :show-suggestions="false" /></details>
      <button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved'" @click="analyze">{{ store.busy ? '正在分析…' : '生成案情与证据分析' }}</button>
      <p v-if="item.analysis" class="small muted plan-step-body">已生成分析，建议与法律来源在右侧查看。</p>
    </template>
    <ProgressRecordForm v-if="['platform', 'authority', 'followup'].includes(step.type)" :item="item" :channel="step.type === 'platform' ? 'platform' : ''" :title="step.type === 'platform' ? '记录平台答复' : step.type === 'authority' ? '记录渠道核对结果' : '补充处理进展'" />
    <RouterLink v-if="step.type === 'followup'" :to="{ path: '/follow-up', query: { case: item.id } }" class="btn btn-primary">记录受理与履行反馈</RouterLink>
    <slot />
  </section>
</template>
