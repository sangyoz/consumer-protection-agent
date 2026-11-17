<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import { CHANNELS, ACCEPT_STATUSES } from '../../domain/case'
const props = defineProps({ item: Object, channel: { type: String, default: '' }, title: { type: String, default: '记录实际处理结果' } })
const store = useCasesStore()
const form = reactive({ channel: '', acceptStatus: '', caseNo: '', deadline: '', note: '' })
const saved = ref(false)
watch([() => props.item.id, () => props.channel], () => { Object.assign(form, { channel: props.channel, acceptStatus: '', caseNo: '', deadline: '', note: '' }); saved.value = false }, { immediate: true })
const channels = [...CHANNELS, {key: 'legal_aid', name: '法律援助或专业咨询'}]
const entries = computed(() => [...(props.item.followups || [])].filter(row => !props.channel || row.channel === props.channel).reverse().slice(0, 3))
async function save() {
  if (!form.note.trim()) return
  const result = await store.act('updateProgress', props.item.id, {
    note: form.note.trim(), channel: form.channel || null, acceptStatus: form.acceptStatus || null,
    caseNo: form.caseNo.trim() || null, deadline: form.deadline || null,
  })
  if (result) { form.note = ''; saved.value = true; store.notify('处理记录已保存，后续路径已重新评估') }
}
</script>
<template>
  <section class="step-form-section">
    <h3>{{ title }}</h3>
    <p class="small muted">在对应平台或渠道实际处理后，把答复记在这里。保存记录不会替你提交申请，也不会自动结案。</p>
    <form @submit.prevent="save">
      <fieldset :disabled="store.busy || item.stage === 'resolved'" class="step-fieldset">
        <div class="form-grid">
          <label class="field">处理渠道<select v-model="form.channel"><option value="">暂未确定</option><option v-for="entry in channels" :key="entry.key" :value="entry.key">{{ entry.name }}</option></select></label>
          <label class="field">受理状态<select v-model="form.acceptStatus"><option value="">暂未确定</option><option v-for="(name, key) in ACCEPT_STATUSES" :key="key" :value="key">{{ name }}</option></select></label>
          <label class="field">受理编号（选填）<input v-model="form.caseNo" maxlength="100" placeholder="填写实际收到的编号" /></label>
          <label class="field">答复期限（选填）<input v-model="form.deadline" type="date" /></label>
        </div>
        <label class="field">答复或处理进展<textarea v-model="form.note" rows="3" required maxlength="3000" placeholder="例如：平台要求补充故障视频，商家仍拒绝退款。" /></label>
        <button class="btn btn-primary" type="submit" :disabled="!form.note.trim()">{{ store.busy ? '正在保存并评估…' : '保存记录并评估后续步骤' }}</button>
      </fieldset>
    </form>
    <p v-if="saved" class="small gap-ok" role="status">记录已保存。下方可以查看最近记录。</p>
    <details v-if="entries.length" class="audit-trace" open><summary>最近处理记录</summary><article v-for="entry in entries" :key="entry.id" class="step-record"><small class="muted">{{ new Date(entry.createdAt).toLocaleString('zh-CN') }} · {{ ACCEPT_STATUSES[entry.acceptStatus] || '已记录' }}</small><p>{{ entry.note }}</p><p v-if="entry.caseNo" class="small muted">编号：{{ entry.caseNo }}</p></article></details>
  </section>
</template>
