<script setup>
import { computed, reactive, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import GoalPlanPanel from './GoalPlanPanel.vue'
import MaterialList from './MaterialList.vue'
import EvidenceChecklist from './EvidenceChecklist.vue'
import ProgressRecordForm from './ProgressRecordForm.vue'
import RefundCalculator from './RefundCalculator.vue'
import AnalysisPanel from './AnalysisPanel.vue'
import { dataMode } from '../../api'
const props = defineProps({ item: Object, step: Object })
const store = useCasesStore()
const guides = {
  identity: ['核对订单或合同上列明的经营者名称。', '对照付款收款方、店铺名称与经营主体；不一致时保留截图并询问原因。', '在下方填写已核对的信息；暂不清楚的内容可以留空。'],
  evidence: ['在下方上传材料，或勾选你已经保存在手上的证据。', '订单与付款记录优先；与商家还没有沟通过时，可暂不确认沟通记录。'],
  platform: ['核对交易平台、订单和当前售后状态。', '查看平台官方售后入口、申请期限与材料要求，记录平台答复。', '系统不会替你提交申请。'],
  authority: ['先确认经营主体、行业和属地。', '向官方渠道核对受理范围、提交材料与是否需补充信息。', '记录不受理的具体原因，供后续调整路径。'],
  followup: ['记录受理编号、处理期限、补材料要求和实际履行情况。', '商家口头同意不代表已履行；确认款项到账或诉求落实后再结案。'],
}
const guide = computed(() => guides[props.step?.type] || [])
const identity = reactive({ merchant: '', payee: '', creditCode: '' })
watch(() => props.item.id, () => Object.keys(identity).forEach(key => { identity[key] = props.item[key] || '' }), { immediate: true })
async function saveIdentity() {
  if (!identity.merchant.trim()) { store.notify('请填写订单或合同上的经营者名称，暂不清楚可在步骤结果中说明'); return }
  if (await store.act('updateCase', props.item.id, { merchant: identity.merchant.trim(), payee: identity.payee.trim(), creditCode: identity.creditCode.trim() })) store.notify('主体信息已保存，后续路径已重新评估')
}
async function upload(event) {
  const files = [...event.target.files]; event.target.value = ''
  if (!files.length) return
  if (files.length > 5 || files.some(file => !/\.(pdf|docx|png|jpe?g|txt)$/i.test(file.name) || file.size > 10 * 1024 * 1024 || !file.size)) { store.notify('每次最多5份非空文件，单份不超过10 MB，支持PDF、DOCX、图片和TXT'); return }
  if (await store.act('addMaterials', props.item.id, files)) store.notify(dataMode === 'mock' ? '演示模式仅记录文件名，未保存文件内容' : '材料已上传，文件内容仍待核验')
}
async function analyze() {
  if (await store.act('analyze', props.item.id)) store.notify('已生成案情分析，请展开下方分析结果查看')
}
</script>

<template>
  <section class="panel content-panel">
    <div class="panel-title"><h2>{{ step.title }}</h2><span class="subtle-tag">本案处理步骤</span></div>
    <p class="body-copy muted">{{ step.reason }}</p>
    <div v-if="step.type === 'calculation'" class="plan-step-body"><RefundCalculator :item="item" /><GoalPlanPanel :item="item" /></div>
    <template v-else><ul class="checklist plan-step-body"><li v-for="text in guide" :key="text">{{ text }}</li></ul></template>
    <form v-if="step.type === 'identity'" @submit.prevent="saveIdentity"><fieldset class="step-fieldset" :disabled="store.busy || item.stage === 'resolved'"><label class="field">订单或合同上的经营者名称<input v-model="identity.merchant" maxlength="200" required placeholder="请按订单或合同原文填写" /></label><label class="field">实际收款方（选填）<input v-model="identity.payee" maxlength="200" /></label><label class="field">统一社会信用代码（选填）<input v-model="identity.creditCode" maxlength="30" pattern="[A-Za-z0-9 ]*" /></label><button class="btn btn-primary" type="submit">保存主体信息并评估后续</button></fieldset></form>
    <template v-if="step.type === 'evidence'">
      <p class="notice-box">这一步用于把“描述里说有的证据”整理成清单。先上传或确认已有材料，再记录本步结果；你也可以先查看下一步。</p>
      <label class="upload-btn evidence-upload" :class="{ disabled: store.busy || item.stage === 'resolved' }">{{ store.busy ? '正在保存并评估…' : '上传证据材料' }}<input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg,.txt" multiple :disabled="store.busy || item.stage === 'resolved'" @change="upload" /></label>
      <p class="fine-print">每次最多5份，单份不超过10 MB。支持PDF、DOCX、图片和TXT；视频请先自行保存，可上传关键截图。</p>
      <EvidenceChecklist :item="item" />
      <details class="plan-step-body"><summary>已上传材料（{{ item.materials.length }}份）</summary><MaterialList :item="item" :show-suggestions="false" /></details>
      <button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved'" @click="analyze">{{ store.busy ? '正在分析…' : '生成案情与证据分析' }}</button>
      <details v-if="item.analysis" class="plan-step-body" open><summary>查看已生成的分析结果</summary><AnalysisPanel :item="item" /></details>
    </template>
    <ProgressRecordForm v-if="['platform', 'authority', 'followup'].includes(step.type)" :item="item" :channel="step.type === 'platform' ? 'platform' : ''" :title="step.type === 'platform' ? '记录平台答复' : step.type === 'authority' ? '记录渠道核对结果' : '补充处理进展'" />
    <div class="notice-box plan-step-body"><strong>何时可以进入下一步</strong><p>{{ step.completion_condition || '记录处理结果后，根据新情况调整。' }}</p></div>
    <RouterLink v-if="step.type === 'followup'" :to="{ path: '/follow-up', query: { case: item.id } }" class="btn btn-primary">记录受理与履行反馈</RouterLink>
    <slot />
  </section>
</template>
