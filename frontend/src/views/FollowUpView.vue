<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useCasesStore } from '../stores/cases'
import { stages, CHANNELS, ACCEPT_STATUSES } from '../domain/case'
import AppIcon from '../components/AppIcon.vue'
import StatusBadge from '../components/StatusBadge.vue'

const store = useCasesStore()
const route = useRoute()
const selected = ref('')
const note = ref('')
const stage = ref('')
const confirmed = ref(false)
const channel = ref('')
const caseNo = ref('')
const acceptStatus = ref('')
const deadline = ref('')
const resolvedWay = ref('')
const actualAmount = ref('')
const expectedMet = ref('')
const resolutionNote = ref('')

const item = computed(() => store.items.find(c => c.id === selected.value))
const followups = computed(() => [...(item.value?.followups || [])].reverse())

const RESOLVED_WAYS = [{ key: 'negotiation', name: '与商家协商解决' }, ...CHANNELS.map(c => ({ key: c.key, name: c.name })), { key: 'other', name: '其他方式' }]
const EXPECTED_MET = { yes: '达到预期', partial: '部分达到', no: '未达到' }

function channelName(key) {
  return CHANNELS.find(c => c.key === key)?.name || RESOLVED_WAYS.find(w => w.key === key)?.name || key || ''
}

const usedChannels = computed(() => {
  const keys = [...new Set((item.value?.followups || []).map(f => f.channel).filter(Boolean))]
  return keys.map(channelName).filter(Boolean)
})

function resetForm() {
  stage.value = ''
  confirmed.value = false
  channel.value = ''
  caseNo.value = ''
  acceptStatus.value = ''
  deadline.value = ''
  resolvedWay.value = ''
  actualAmount.value = ''
  expectedMet.value = ''
  resolutionNote.value = ''
}

onMounted(async () => {
  await store.list()
  selected.value = store.items.some(c => c.id === route.query.case) ? route.query.case : store.items[0]?.id || ''
})

async function save() {
  if (!note.value.trim() || !item.value || (stage.value === 'resolved' && !confirmed.value)) return
  const resolution = stage.value === 'resolved' && confirmed.value ? {
    resolvedWay: resolvedWay.value,
    actualAmount: actualAmount.value === '' ? '' : Number(actualAmount.value),
    expectedMet: expectedMet.value || null,
    summary: resolutionNote.value.trim(),
    closedAt: new Date().toISOString(),
  } : null
  const payload = {
    note: note.value.trim(),
    stage: stage.value || null,
    confirmed: confirmed.value,
    channel: channel.value || null,
    caseNo: caseNo.value.trim() || null,
    acceptStatus: acceptStatus.value || null,
    deadline: deadline.value || null,
    resolution,
  }
  if (await store.act('updateProgress', item.value.id, payload)) {
    note.value = ''
    resetForm()
    store.notify('处理进度已保存')
  }
}
</script>

<template>
  <div class="page followup-page">
    <div class="page-heading followup-heading"><div><div class="eyebrow">持续跟进</div><h1>处理到哪一步了？</h1></div><label class="followup-picker-inline"><span>案件</span><select v-model="selected" @change="resetForm"><option v-for="c in store.items" :key="c.id" :value="c.id">{{ c.title }}</option></select></label></div>
    <div v-if="store.error" class="error-banner" role="alert">{{ store.error }}</div>
    <div v-if="store.busy && !store.items.length" class="empty-state">正在加载案件…</div>
    <div v-else-if="!store.items.length" class="panel empty-state"><h2>还没有可以跟进的案件</h2><RouterLink to="/cases/new" class="btn btn-primary">新建案件</RouterLink></div>

    <template v-else>

      <div v-if="item" class="followup-grid">
        <section class="panel content-panel">
          <div class="panel-title"><h2>处理记录</h2><StatusBadge :stage="item.stage" /></div>

          <div v-if="item.resolution" class="resolution-card">
            <div class="panel-title"><h3>结案总结</h3><em class="tag tag-muted">{{ EXPECTED_MET[item.resolution.expectedMet] || '未填写预期' }}</em></div>
            <dl class="followup-meta">
              <div v-if="item.resolution.resolvedWay"><dt>解决方式</dt><dd>{{ channelName(item.resolution.resolvedWay) }}</dd></div>
              <div v-if="item.resolution.actualAmount !== '' && item.resolution.actualAmount != null"><dt>实际金额</dt><dd>{{ Number(item.resolution.actualAmount).toLocaleString('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 2 }) }}</dd></div>
              <div v-if="usedChannels.length"><dt>采取渠道</dt><dd>{{ usedChannels.join('、') }}</dd></div>
              <div v-if="item.resolution.closedAt"><dt>结案时间</dt><dd>{{ new Date(item.resolution.closedAt).toLocaleString('zh-CN') }}</dd></div>
            </dl>
            <p v-if="item.resolution.summary" class="resolution-summary">{{ item.resolution.summary }}</p>
          </div>

          <div v-if="followups.length" class="followup-list">
            <article v-for="entry in followups" :key="entry.id" class="followup-card">
              <div class="followup-card-head">
                <time>{{ new Date(entry.createdAt).toLocaleString('zh-CN') }}</time>
                <em v-if="entry.acceptStatus" class="tag">{{ ACCEPT_STATUSES[entry.acceptStatus] || entry.acceptStatus }}</em>
              </div>
              <p>{{ entry.note }}</p>
              <dl v-if="entry.channel || entry.caseNo || entry.deadline" class="followup-meta">
                <div v-if="entry.channel"><dt>渠道</dt><dd>{{ channelName(entry.channel) }}</dd></div>
                <div v-if="entry.caseNo"><dt>编号</dt><dd>{{ entry.caseNo }}</dd></div>
                <div v-if="entry.deadline"><dt>处理期限</dt><dd>{{ entry.deadline }}</dd></div>
              </dl>
            </article>
          </div>

          <ol class="timeline">
            <li v-for="entry in [...item.timeline].reverse()" :key="entry.id"><span class="timeline-dot"></span><time>{{ new Date(entry.createdAt).toLocaleString('zh-CN') }}</time><p>{{ entry.text }}</p></li>
          </ol>
          <RouterLink :to="`/cases/${item.id}/analysis`" class="text-link">返回案件工作台<AppIcon name="arrow" :size="16" /></RouterLink>
        </section>

        <form class="panel content-panel" @submit.prevent="save">
          <h2>添加新的处理反馈</h2>
          <div class="followup-form-body">
          <label class="field">发生了什么？<textarea v-model="note" rows="5" maxlength="3000" required placeholder="例如：商家承诺三个工作日内退款，仍需等待实际到账。"></textarea></label>

          <div class="form-grid">
            <label class="field">投诉/反馈渠道
              <select v-model="channel">
                <option value="">未选择渠道</option>
                <option v-for="c in CHANNELS" :key="c.key" :value="c.key">{{ c.name }}</option>
              </select>
            </label>
            <label class="field">受理编号<input v-model="caseNo" maxlength="100" placeholder="平台工单或投诉编号" /></label>
            <label class="field">受理状态
              <select v-model="acceptStatus">
                <option value="">未填写</option>
                <option v-for="(label, value) in ACCEPT_STATUSES" :key="value" :value="value">{{ label }}</option>
              </select>
            </label>
            <label class="field">处理期限<input v-model="deadline" type="date" /></label>
          </div>

          <label class="field">更新案件状态
            <select v-model="stage"><option value="">保持当前状态</option><option v-for="(label, value) in stages" :key="value" :value="value">{{ label }}</option></select>
          </label>
          <label v-if="stage === 'resolved'" class="check-row"><input v-model="confirmed" type="checkbox" required />我确认退款已到账或其他诉求已实际履行。</label>

          <div v-if="stage === 'resolved' && confirmed" class="resolution-form">
            <div class="form-grid">
              <label class="field">最终解决方式
                <select v-model="resolvedWay">
                  <option value="">请选择</option>
                  <option v-for="way in RESOLVED_WAYS" :key="way.key" :value="way.key">{{ way.name }}</option>
                </select>
              </label>
              <label class="field">实际退款/赔偿金额（元）<input v-model="actualAmount" type="number" min="0" step="0.01" /></label>
              <label class="field">是否达到预期
                <select v-model="expectedMet">
                  <option value="">请选择</option>
                  <option v-for="(label, value) in EXPECTED_MET" :key="value" :value="value">{{ label }}</option>
                </select>
              </label>
            </div>
            <label class="field">结案备注<textarea v-model="resolutionNote" rows="3" maxlength="1000" placeholder="例如：退款已全额到账，剩余优惠券补偿未主张。"></textarea></label>
          </div>

          </div>
          <div class="followup-actions">
            <p class="fine-print">商家口头同意或投诉提交成功，均不代表问题已解决。</p>
            <button class="btn btn-primary" :disabled="store.busy || !note.trim() || (stage === 'resolved' && !confirmed)">{{ store.busy ? '正在保存…' : '保存处理反馈' }}</button>
          </div>
        </form>
      </div>
    </template>
  </div>
</template>
