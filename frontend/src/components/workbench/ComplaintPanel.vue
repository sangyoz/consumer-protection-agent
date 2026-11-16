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
  if (await store.act('generateComplaint', props.item.id)) store.notify('投诉内容已生成，请核对后自行提交')
}

async function copy() {
  try { await navigator.clipboard.writeText(props.item.complaint); store.notify('投诉草稿已复制') } catch { store.notify('复制失败，请手动选择草稿文本') }
}
</script>

<template>
  <section class="panel content-panel">
    <div class="panel-title"><h2>投诉材料准备</h2><span class="subtle-tag">用户核对后提交</span></div>
    <p class="muted body-copy">依据已填写的案件信息与上传材料，整理成一段可直接提交的投诉内容。</p>

    <div class="panel-actions complaint-actions">
      <button class="btn btn-primary" :disabled="store.busy || item.stage === 'resolved'" @click="generate">{{ store.busy ? '正在整理…' : '生成投诉内容' }}</button>
    </div>

    <div class="panel-title complaint-preview-head"><h3>投诉内容</h3><button v-if="item.complaint" class="text-link" @click="copy"><AppIcon name="copy" :size="15" />复制内容</button></div>
    <pre v-if="item.complaint" class="complaint-preview">{{ item.complaint }}</pre>
    <div v-else class="inline-empty"><AppIcon name="file" :size="30" /><p>还没有投诉内容</p><span class="small muted">点击上方按钮，会依据已填写的案件信息整理成一段可直接提交的投诉内容。</span></div>

    <div class="notice-box"><strong>下一步由你确认</strong><p>内容只保存在本案件，不会向外部平台提交；核对后可复制到对应渠道填写。</p></div>
  </section>
</template>
