<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import { MATERIAL_KINDS } from '../../domain/case'

const props = defineProps({ item: Object })
const store = useCasesStore()

const form = reactive({ basic: '', further: '', negotiable: '', targetAmount: '', basis: '', confirmed: false, evidence: '' })
const saved = ref(false)

watch(() => props.item, val => {
  const plan = val?.goalPlan || {}
  Object.assign(form, {
    basic: plan.basic || '',
    further: plan.further || '',
    negotiable: plan.negotiable || '',
    targetAmount: plan.targetAmount ?? '',
    basis: plan.basis || '',
    confirmed: !!plan.confirmed,
    evidence: plan.evidence || '',
  })
  saved.value = false
}, { immediate: true })

const materialSummary = computed(() => {
  const kinds = [...new Set((props.item.materials || []).map(m => m.kind))]
  return kinds.map(k => MATERIAL_KINDS[k] || k)
})

async function save() {
  const plan = {
    ...(props.item.goalPlan || {}),
    basic: form.basic.trim(),
    further: form.further.trim(),
    negotiable: form.negotiable.trim(),
    targetAmount: form.targetAmount === '' ? '' : Number(form.targetAmount),
    basis: form.basis.trim(),
    confirmed: form.confirmed,
    evidence: form.evidence,
  }
  if (await store.act('updateCase', props.item.id, { goalPlan: plan })) {
    saved.value = true
    store.notify(form.confirmed ? '诉求已确认并保存' : '诉求草稿已保存，尚未确认')
  }
}
</script>

<template>
  <div class="goal-plan">
    <div class="panel-title"><h3>确定诉求与谈判目标</h3><span class="small muted">分层整理，由你最终确认</span></div>

    <div class="goal-tier">
      <label class="field">
        <span class="field-caption">基础诉求<em class="tier-hint">法律或合同支持、可优先主张的权利</em></span>
        <textarea v-model="form.basic" rows="2" maxlength="500" placeholder="例如：符合条件时要求退货退款。"></textarea>
      </label>
      <label class="field">
        <span class="field-caption">进一步诉求<em class="tier-hint">有相应事实和依据时可提出的额外要求</em></span>
        <textarea v-model="form.further" rows="2" maxlength="500" placeholder="例如：赔偿实际损失。"></textarea>
      </label>
      <label class="field">
        <span class="field-caption">协商诉求<em class="tier-hint">法律未直接要求、可在协商中争取的补偿</em></span>
        <textarea v-model="form.negotiable" rows="2" maxlength="500" placeholder="例如：额外服务、优惠或适当补偿。"></textarea>
      </label>
    </div>

    <div class="form-grid">
      <label class="field">目标金额（元）<input v-model="form.targetAmount" type="number" min="0" step="0.01" placeholder="可以留空" /></label>
      <label class="field">金额计算依据<textarea v-model="form.basis" rows="2" maxlength="1000" placeholder="例如：剩余未消费时长 × 单次单价。"></textarea></label>
    </div>

    <div class="goal-evidence">
      <span class="field-caption">现有证据支持</span>
      <p v-if="materialSummary.length" class="small muted">{{ materialSummary.join('、') }}</p>
      <p v-else class="small muted">暂无可核对的材料。</p>
      <p v-if="form.evidence" class="small">{{ form.evidence }}</p>
      <span class="fine-print">证据是否充分、法律依据与金额合理性由后续分析模块补充，本页不替你决定接受多少补偿。</span>
    </div>

    <label class="check-row"><input v-model="form.confirmed" type="checkbox" />我已核对以上诉求，确认作为当前谈判目标。</label>
    <div class="goal-actions">
      <span v-if="item.goalPlan?.confirmed" class="small muted gap-ok">诉求已确认</span>
      <button class="btn btn-secondary" :disabled="store.busy || item.stage === 'resolved'" @click="save">{{ store.busy ? '正在保存…' : '保存诉求' }}</button>
    </div>
  </div>
</template>
