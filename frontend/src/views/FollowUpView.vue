<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useCasesStore } from '../stores/cases'
import { stages } from '../domain/case'
import AppIcon from '../components/AppIcon.vue'
import StatusBadge from '../components/StatusBadge.vue'
const store = useCasesStore()
const route = useRoute()
const selected = ref('')
const note = ref('')
const stage = ref('')
const confirmed = ref(false)
const item = computed(() => store.items.find(c => c.id === selected.value))
onMounted(async () => { await store.list(); selected.value = store.items.some(c => c.id === route.query.case) ? route.query.case : store.items[0]?.id || '' })
async function save() {
  if (!note.value.trim() || !item.value || (stage.value === 'resolved' && !confirmed.value)) return
  if (await store.act('updateProgress', item.value.id, { note: note.value.trim(), stage: stage.value || null, confirmed: confirmed.value })) { note.value = ''; stage.value = ''; confirmed.value = false; store.notify('处理进度已保存') }
}
</script>
<template><div class="page"><div class="page-heading"><div><div class="eyebrow">持续跟进</div><h1>处理到哪一步了？</h1><p>记下新的回复、处理期限和实际结果，方便下一次继续。</p></div></div><div v-if="store.error" class="error-banner" role="alert">{{ store.error }}</div><div v-if="store.busy && !store.items.length" class="empty-state">正在加载案件…</div><div v-else-if="!store.items.length" class="panel empty-state"><h2>还没有可以跟进的案件</h2><RouterLink to="/cases/new" class="btn btn-primary">新建案件</RouterLink></div><template v-else><label class="field followup-picker">选择案件<select v-model="selected" @change="stage = ''; confirmed = false"><option v-for="c in store.items" :key="c.id" :value="c.id">{{ c.title }}</option></select></label><div v-if="item" class="followup-grid"><section class="panel content-panel"><div class="panel-title"><h2>处理记录</h2><StatusBadge :stage="item.stage" /></div><ol class="timeline"><li v-for="entry in [...item.timeline].reverse()" :key="entry.id"><span class="timeline-dot"></span><time>{{ new Date(entry.createdAt).toLocaleString('zh-CN') }}</time><p>{{ entry.text }}</p></li></ol><RouterLink :to="`/cases/${item.id}/analysis`" class="text-link">返回案件工作台<AppIcon name="arrow" :size="16" /></RouterLink></section><form class="panel content-panel" @submit.prevent="save"><h2>添加新的处理反馈</h2><label class="field">发生了什么？<textarea v-model="note" rows="5" maxlength="3000" required placeholder="例如：商家承诺三个工作日内退款，仍需等待实际到账。"></textarea></label><label class="field">更新案件状态<select v-model="stage"><option value="">保持当前状态</option><option v-for="(label, value) in stages" :key="value" :value="value">{{ label }}</option></select></label><label v-if="stage === 'resolved'" class="check-row"><input v-model="confirmed" type="checkbox" required />我确认退款已到账或其他诉求已实际履行。</label><p class="fine-print">商家口头同意或投诉提交成功，均不代表问题已解决。</p><button class="btn btn-primary" :disabled="store.busy || !note.trim() || (stage === 'resolved' && !confirmed)">{{ store.busy ? '正在保存…' : '保存处理反馈' }}</button></form></div></template></div></template>
