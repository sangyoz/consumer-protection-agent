<script setup>
import { computed, reactive, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import { money } from '../../domain/case'
const props = defineProps({ item: Object })
const store = useCasesStore()
const form = reactive({ paid: '', total: '', used: '' })
watch(() => props.item.id, () => Object.assign(form, { paid: props.item.amount || '', total: '', used: '', ...props.item.goalPlan?.calculation }), { immediate: true })
const estimate = computed(() => {
  if ([form.paid, form.total, form.used].some(value => value === '')) return null
  const [paid, total, used] = [form.paid, form.total, form.used].map(Number)
  if (![paid, total, used].every(Number.isFinite) || paid < 0 || total <= 0 || used < 0 || used > total) return null
  return Math.round(paid * (total - used) / total * 100) / 100
})
async function save() {
  if (estimate.value === null) return
  const basis = `按均价估算：${form.paid}元 ×（${form.total} − ${form.used}）÷ ${form.total} = ${estimate.value}元。未计优惠、赠送、已约定费用或其他争议因素，待核对合同。`
  if (await store.act('updateCase', props.item.id, { goalPlan: { ...(props.item.goalPlan || {}), targetAmount: estimate.value, basis, confirmed: false, calculation: { ...form } } })) store.notify('估算已保存到诉求草稿，请核对合同与费用约定')
}
</script>
<template>
  <section class="step-form-section">
    <h3>估算未消费部分</h3><p class="small muted">适用于按次数或时长均摊的初步计算，不代表最终应退金额。总量与已使用量请使用同一单位。</p>
    <div class="form-grid"><label class="field">实际支付金额（元）<input v-model="form.paid" type="number" min="0" step="0.01" :disabled="store.busy || item.stage === 'resolved'" /></label><label class="field">总次数或总时长<input v-model="form.total" type="number" min="0.01" step="any" :disabled="store.busy || item.stage === 'resolved'" /></label><label class="field">已使用次数或时长<input v-model="form.used" type="number" min="0" step="any" :disabled="store.busy || item.stage === 'resolved'" /></label></div>
    <p class="notice-box" role="status">{{ estimate === null ? '填写有效金额、总量和已用量后显示估算；已用量不能大于总量。' : `未消费部分估算：${money(estimate)}` }}</p>
    <button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved' || estimate === null" @click="save">将估算保存到诉求草稿</button>
  </section>
</template>
