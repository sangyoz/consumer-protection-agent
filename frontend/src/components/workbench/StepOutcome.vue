<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCasesStore } from '../../stores/cases'
import { TERMINAL_STEPS, STEP_STATUS } from '../../domain/plan'
const props = defineProps({ item: Object, step: Object })
const store = useCasesStore()
const router = useRouter()
const note = ref('')
const placeholder = computed(() => ({ evidence: '例如：订单和付款截图已整理。', platform: '例如：平台拒绝处理，原因是……', negotiation: '例如：商家仍拒绝退款。', calculation: '例如：已核对剩余课时及退款估算。' })[props.step?.type] || '记录本步骤实际处理结果。')
async function report(status) {
  const result = await store.act('stepFeedback', props.item.id, props.step.id, { status, note: note.value.trim() })
  if (result) { store.notify('步骤结果已保存'); router.push(`/cases/${result.id}/${result.plan.current_step_id}`) }
}
</script>
<template>
  <section v-if="step && step.type !== 'other'" class="step-form-section">
    <h3>记录本步结果</h3>
    <template v-if="!TERMINAL_STEPS.includes(step.status) && item.stage !== 'resolved'">
      <label class="field">本步骤实际结果<textarea v-model="note" rows="2" maxlength="2000" :placeholder="placeholder" :disabled="store.busy" /></label>
      <div class="plan-feedback-actions"><button class="btn btn-primary" :disabled="store.busy || !note.trim()" @click="report('completed')">已完成</button><button class="btn btn-secondary" :disabled="store.busy || !note.trim()" @click="report('failed')">未解决</button><button class="text-link" :disabled="store.busy || !note.trim()" @click="report('skipped')">不适用</button></div>
    </template>
    <p v-else class="notice-box">{{ STEP_STATUS[step.status] }}{{ step.note ? '：' + step.note : '' }}</p>
    <p class="fine-print">记录结果后进入原定的下一步，案件步骤与顺序保持不变。</p>
  </section>
</template>
