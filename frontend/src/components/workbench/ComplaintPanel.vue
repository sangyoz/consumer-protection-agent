<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import { REQUIRED_MATERIALS, MATERIAL_KINDS } from '../../domain/case'
import AppIcon from '../AppIcon.vue'

const props = defineProps({ item: Object })
const store = useCasesStore()

const steps = ['投诉对象', '事实经过', '诉求内容', '证据附件']
const step = ref(0)
const form = reactive({ merchant: '', payee: '', creditCode: '', platform: '', summary: '', goal: '' })
const selectedIds = ref([])

watch(() => props.item, val => {
  if (!val) return
  Object.assign(form, { merchant: val.merchant || '', payee: val.payee || '', creditCode: val.creditCode || '', platform: val.platform || '', summary: val.summary || '', goal: val.goal || '' })
  const saved = Array.isArray(val.complaintAttachments) ? val.complaintAttachments : []
  selectedIds.value = saved.length ? val.materials.map(m => m.id).filter(id => saved.includes(id)) : val.materials.map(m => m.id)
}, { immediate: true })

const counts = computed(() => {
  const map = {}
  props.item.materials.forEach(m => { map[m.kind] = (map[m.kind] || 0) + 1 })
  return map
})

const checks = computed(() => REQUIRED_MATERIALS.map(entry => ({ ...entry, count: counts.value[entry.kind] || 0 })))

const selectedMaterials = computed(() => props.item.materials.filter(m => selectedIds.value.includes(m.id)))

const stepValid = computed(() => {
  if (step.value === 0) return form.merchant.trim() || form.payee.trim()
  if (step.value === 1) return form.summary.trim().length > 0
  if (step.value === 2) return form.goal.trim().length > 0
  return true
})

async function toggle(id) {
  const index = selectedIds.value.indexOf(id)
  if (index >= 0) selectedIds.value.splice(index, 1)
  else selectedIds.value.push(id)
  await store.act('updateCase', props.item.id, { complaintAttachments: selectedIds.value })
}

function next() { if (stepValid.value) step.value += 1 }
function prev() { step.value -= 1 }

async function generate() {
  const payload = {
    merchant: form.merchant.trim(),
    payee: form.payee.trim(),
    creditCode: form.creditCode.trim().toUpperCase().replace(/\s/g, ''),
    platform: form.platform.trim(),
    summary: form.summary.trim(),
    goal: form.goal.trim(),
    complaintAttachments: selectedIds.value,
  }
  await store.act('updateCase', props.item.id, payload)
  if (await store.act('generateComplaint', props.item.id)) store.notify('投诉草稿已生成，尚未对外提交')
}

async function copy() {
  try { await navigator.clipboard.writeText(props.item.complaint); store.notify('投诉草稿已复制') } catch { store.notify('复制失败，请手动选择草稿文本') }
}
</script>

<template>
  <section class="panel content-panel">
    <div class="panel-title"><h2>投诉材料准备</h2><span class="subtle-tag">用户核对后提交</span></div>
    <p class="muted body-copy">按步骤核对投诉对象、事实、诉求和证据；已有信息会自动带入，可在表单中修改。</p>

    <div class="evidence-checks">
      <div v-for="check in checks" :key="check.kind">
        <AppIcon :name="check.count ? 'check' : 'file'" :size="17" />
        <span>{{ check.label }}</span>
        <span class="small muted">{{ check.count ? `${check.count} 份` : '待补充' }}</span>
      </div>
      <div>
        <AppIcon :name="item.messages.filter(m => m.role === 'merchant').length ? 'check' : 'file'" :size="17" />
        <span>与商家的沟通记录</span>
        <span class="small muted">{{ item.messages.filter(m => m.role === 'merchant').length }} 条商家回复</span>
      </div>
    </div>

    <div class="stepper">
      <span v-for="(label, index) in steps" :key="label" :class="{ done: index < step, current: index === step }"><i>{{ index + 1 }}</i>{{ label }}</span>
    </div>

    <form class="complaint-form" @submit.prevent="generate">
      <div v-if="step === 0" class="form-grid">
        <label class="field">商家名称<input v-model="form.merchant" maxlength="200" /></label>
        <label class="field">实际收款方<input v-model="form.payee" maxlength="200" /></label>
        <label class="field">交易平台<input v-model="form.platform" maxlength="100" /></label>
        <label class="field">统一社会信用代码<input v-model="form.creditCode" maxlength="30" /></label>
      </div>

      <div v-if="step === 1" class="field">
        <span class="field-caption">事实与经过</span>
        <textarea v-model="form.summary" rows="5" maxlength="10000" required></textarea>
      </div>

      <div v-if="step === 2" class="field">
        <span class="field-caption">希望如何解决</span>
        <textarea v-model="form.goal" rows="3" maxlength="1000" required></textarea>
      </div>

      <div v-if="step === 3" class="evidence-pick">
        <p class="small muted">勾选随投诉一并提交的材料（默认全部纳入）。</p>
        <label v-for="file in item.materials" :key="file.id" class="evidence-pick-row">
          <input type="checkbox" :checked="selectedIds.includes(file.id)" :disabled="item.stage === 'resolved'" @change="toggle(file.id)" />
          <span><strong>{{ file.name }}</strong><em>{{ MATERIAL_KINDS[file.kind] || MATERIAL_KINDS.other }}</em></span>
        </label>
        <p v-if="!item.materials.length" class="small muted">暂无可勾选的材料，可先在左侧补充证据。</p>
      </div>

      <div class="step-nav">
        <button v-if="step > 0" type="button" class="btn btn-secondary" @click="prev">上一步</button>
        <button v-if="step < steps.length - 1" type="button" class="btn btn-primary" :disabled="!stepValid" @click="next">下一步<AppIcon name="arrow" :size="16" /></button>
      </div>
    </form>

    <div class="panel-title"><h3>投诉内容预览</h3><button v-if="item.complaint" class="text-link" @click="copy"><AppIcon name="copy" :size="15" />复制草稿</button></div>
    <pre v-if="item.complaint" class="complaint-preview">{{ item.complaint }}</pre>
    <div v-else class="inline-empty"><AppIcon name="file" :size="30" /><p>还没有投诉草稿</p><span class="small muted">完成上方步骤后，点击下方按钮整理。</span></div>

    <div v-if="selectedMaterials.length" class="draft-attachments">
      <span class="field-caption">草稿附件清单</span>
      <ul><li v-for="file in selectedMaterials" :key="file.id">{{ file.name }}</li></ul>
    </div>

    <div class="panel-actions">
      <button class="btn btn-primary" :disabled="store.busy || item.stage === 'resolved' || !stepValid" @click="generate">{{ store.busy ? '正在整理…' : item.complaint ? '重新生成草稿' : '生成投诉材料' }}</button>
      <RouterLink :to="{ path: '/follow-up', query: { case: item.id } }" class="btn btn-secondary">记录处理进度<AppIcon name="arrow" :size="16" /></RouterLink>
    </div>
    <div class="notice-box"><strong>下一步由你确认</strong><p>全国 12315、交易平台售后等渠道可在“其他方案”中查看。本框架仅整理材料，不会向外部平台提交。</p></div>
  </section>
</template>
