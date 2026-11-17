<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCasesStore } from '../../stores/cases'
import { caseSteps, TERMINAL_STEPS, STEP_STATUS } from '../../domain/plan'
const props = defineProps({ item: Object, step: Object })
const store = useCasesStore()
const router = useRouter()
const note = ref('')
const next = computed(() => { const rows = caseSteps(props.item); return rows[rows.findIndex(row => row.id === props.step?.id) + 1] })
async function report(status) {
  const result = await store.act('stepFeedback', props.item.id, props.step.id, { status, note: note.value.trim() })
  if (result) { store.notify('步骤结果已保存，后续路径已调整'); router.push(`/cases/${result.id}/${result.plan.current_step_id}`) }
}
</script>
<template>
  <section v-if="step && step.type !== 'other'" class="step-form-section">
    <h3>这一步处理得怎么样？</h3>
    <p class="small muted">保存资料或查看页面不会自动完成步骤。实际做完后记录结果，Agent 会据此调整后续安排。</p>
    <template v-if="!TERMINAL_STEPS.includes(step.status) && item.stage !== 'resolved'">
      <label class="field">本步骤实际结果<textarea v-model="note" rows="2" maxlength="2000" placeholder="例如：已整理订单和付款截图，故障视频也已保存。" :disabled="store.busy" /></label>
      <div class="plan-feedback-actions"><button class="btn btn-primary" :disabled="store.busy || !note.trim()" @click="report('completed')">完成本步并调整后续</button><button class="btn btn-secondary" :disabled="store.busy || !note.trim()" @click="report('failed')">未解决，评估下一步</button><button class="text-link" :disabled="store.busy || !note.trim()" @click="report('skipped')">这一步不适用</button></div>
    </template>
    <p v-else class="notice-box">{{ STEP_STATUS[step.status] }}{{ step.note ? '：' + step.note : '' }}</p>
    <RouterLink v-if="next" :to="`/cases/${item.id}/${next.id}`" class="text-link step-next">先查看下一步：{{ next.title }}</RouterLink>
  </section>
</template>
