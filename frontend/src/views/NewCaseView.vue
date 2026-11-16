<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCasesStore } from '../stores/cases'
import { api } from '../api'
import { FIELD_LABELS } from '../domain/extract'
import AppIcon from '../components/AppIcon.vue'
import StatusBadge from '../components/StatusBadge.vue'

const router = useRouter()
const store = useCasesStore()
const form = reactive({ title: '', summary: '', merchant: '', amount: '', goal: '', tradeTime: '', platform: '', product: '', payee: '', creditCode: '' })
const errors = reactive({ amount: '', creditCode: '' })
const examples = [{ title: '网购商品质量问题', text: '我网购的商品收到后无法正常使用，已经联系商家，希望协商退货退款。' }, { title: '预付卡退款纠纷', text: '我购买了会员卡，门店突然停业，剩余服务无法使用，希望退还未消费的费用。' }, { title: '售后处理不及时', text: '商品出现问题后申请售后，商家一直让我等待，没有说明具体处理时间。' }]

const extracted = ref({ fields: {}, evidence: [], missing: [] })
const detailsOpen = ref(false)
const composer = ref(null)
const autoFilled = new Set()
const manualFields = reactive(new Set())
let debounceTimer

onMounted(store.list)

const tags = computed(() => extracted.value.evidence
  .filter(item => {
    // 手动改过的字段以表单当前值为准，清空后不再显示标签。
    const value = manualFields.has(item.field) ? form[item.field] : item.value
    return value !== '' && value !== undefined && value !== null
  })
  .map(item => {
    const value = manualFields.has(item.field) ? form[item.field] : item.value
    return {
      field: item.field,
      label: FIELD_LABELS[item.field] || item.field,
      text: item.field === 'amount' ? `¥${value}` : String(value),
    }
  }))
const missing = computed(() => extracted.value.missing)
const showExtract = computed(() => form.summary.trim().length >= 8)

watch(() => form.summary, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(runExtract, 350)
})

async function runExtract() {
  const text = form.summary.trim()
  if (text.length < 8) {
    extracted.value = { fields: {}, evidence: [], missing: [] }
    clearAutoFilled({})
    if (autoFilled.has('title')) {
      form.title = ''
      autoFilled.delete('title')
    }
    return
  }
  try {
    // mock 模式走前端规则，api 模式走后端接口，结构一致。
    const result = await api.extract(text)
    extracted.value = result
    applyFields(result.fields)
    clearAutoFilled(result.fields)
    syncTitle()
  } catch {
    // 识别失败不打断填写，保留上一次结果。
  }
}

/** 标题未手填时跟着诉求和商品走，避免列表里全是"新建消费纠纷"。 */
function syncTitle() {
  if (manualFields.has('title')) return
  const generated = [form.goal, form.product]
    .map(value => String(value || '').trim())
    .filter(Boolean)
    .join(' · ')
  if (form.title === '' || autoFilled.has('title')) {
    form.title = generated
    if (generated) autoFilled.add('title')
    else autoFilled.delete('title')
  }
}

function onFieldInput(key) {
  markManual(key)
  if (key === 'goal' || key === 'product') syncTitle()
}

function applyFields(fields) {
  Object.entries(fields).forEach(([key, value]) => {
    if (manualFields.has(key)) return
    if (form[key] === '' || autoFilled.has(key)) {
      form[key] = value
      autoFilled.add(key)
    }
  })
}

function clearAutoFilled(fields) {
  [...autoFilled].forEach(key => {
    if (key === 'title') return
    if (!(key in fields)) {
      form[key] = ''
      autoFilled.delete(key)
    }
  })
}

function markManual(key) {
  manualFields.add(key)
  autoFilled.delete(key)
}

async function focusField(field) {
  detailsOpen.value = true
  await nextTick()
  const target = composer.value?.querySelector(`[data-field="${field}"]`)
  if (target) {
    target.focus()
    target.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
}

function validate() {
  errors.amount = ''
  errors.creditCode = ''
  const amount = Number(form.amount)
  if (form.amount !== '' && (Number.isNaN(amount) || amount < 0)) errors.amount = '金额不能为负数'
  const code = form.creditCode.trim().replace(/\s/g, '')
  if (code && !/^[A-Za-z0-9]+$/.test(code)) errors.creditCode = '信用代码应为字母或数字'
  return !errors.amount && !errors.creditCode
}

async function submit() {
  if (!form.summary.trim() || !validate()) return
  const payload = { ...form, title: form.title.trim(), summary: form.summary.trim(), amount: Number(form.amount || 0), merchant: form.merchant.trim(), goal: form.goal.trim(), platform: form.platform.trim(), product: form.product.trim(), payee: form.payee.trim(), creditCode: form.creditCode.trim().toUpperCase() }
  const item = await store.create(payload)
  if (item) { store.notify('案件已创建，可以继续补充材料'); router.push(`/cases/${item.id}/analysis`) }
}
</script>

<template>
  <div class="intake-layout">
    <aside class="history-sidebar" aria-label="历史案件">
      <RouterLink to="/cases/new" class="btn btn-primary"><AppIcon name="plus" :size="17" />新建案件</RouterLink>
      <div class="history-heading">历史案件 <span>{{ store.items.length }}</span></div>
      <RouterLink v-for="item in store.items" :key="item.id" :to="`/cases/${item.id}/analysis`" class="history-item"><AppIcon name="chat" :size="16" /><div><strong>{{ item.title }}</strong><StatusBadge :stage="item.stage" /></div></RouterLink>
      <p v-if="!store.items.length" class="fine-print">新建的案件会保存在这里。</p>
      <RouterLink to="/" class="text-link history-home"><AppIcon name="back" :size="15" />查看全部案件</RouterLink>
    </aside>
    <section class="intake-main">
      <div class="intake-welcome">
        <span class="intake-emblem">理</span>
        <div class="eyebrow">有理 · 消费维权助手</div>
        <h1>说说你遇到的问题</h1>
        <p>从发生了什么开始，证据和细节可以慢慢补充。</p>
        <div class="example-list">
          <button v-for="example in examples" :key="example.title" type="button" class="example-chip" @click="form.summary = example.text">{{ example.title }}<AppIcon name="plus" :size="13" /></button>
        </div>
      </div>
      <div class="intake-composer-area">
        <div v-if="store.error" class="error-banner" role="alert">{{ store.error }}</div>
        <form ref="composer" class="intake-composer panel" @submit.prevent="submit">
          <label for="summary" class="field-caption">你遇到了什么消费问题？</label>
          <textarea id="summary" v-model="form.summary" rows="3" maxlength="10000" required placeholder="描述案件的具体情况，例如购买经过、遇到的问题、商家的回复……"></textarea>

          <div v-if="showExtract" class="extract-box">
            <div class="extract-title"><span>已从描述中识别</span><span>规则识别，手动填写优先</span></div>
            <div v-if="tags.length" class="extract-tags">
              <button v-for="tag in tags" :key="tag.field" type="button" class="extract-tag" @click="focusField(tag.field)"><span>{{ tag.label }}</span><strong>{{ tag.text }}</strong></button>
            </div>
            <p v-else class="extract-missing">这段描述里暂未识别到具体字段，可补充金额、平台或商品名称。</p>
            <p v-if="missing.length" class="extract-missing">还缺：{{ missing.map(item => item.label).join('、') }}，可在下方补充。</p>
            <p v-else class="extract-ok">关键信息已识别，核对后即可开始梳理。</p>
          </div>

          <details class="intake-details" :open="detailsOpen" @toggle="detailsOpen = $event.target.open">
            <summary>补充已知信息 <span>选填</span></summary>
            <div class="form-grid">
              <label class="field">案件标题<input v-model="form.title" data-field="title" maxlength="100" placeholder="留空则用「诉求 · 商品」生成" @input="onFieldInput('title')" /></label>
              <label class="field">商家名称<input v-model="form.merchant" data-field="merchant" maxlength="200" placeholder="合同或订单上的商家名称" @input="markManual('merchant')" /></label>
              <label class="field">交易金额（元）<input v-model="form.amount" data-field="amount" type="number" min="0" max="100000000" step="0.01" placeholder="可以留空" @input="markManual('amount')" /><small v-if="errors.amount" class="field-error">{{ errors.amount }}</small></label>
              <label class="field">希望如何解决<input v-model="form.goal" data-field="goal" maxlength="1000" placeholder="例如退货退款、维修" @input="onFieldInput('goal')" /></label>
              <label class="field">交易时间<input v-model="form.tradeTime" data-field="tradeTime" type="date" @input="markManual('tradeTime')" /></label>
              <label class="field">交易平台<input v-model="form.platform" data-field="platform" maxlength="100" placeholder="例如淘宝、京东、抖音、线下门店" @input="markManual('platform')" /></label>
              <label class="field">商品/服务名称<input v-model="form.product" data-field="product" maxlength="200" placeholder="购买的商品或服务" @input="onFieldInput('product')" /></label>
              <label class="field">实际收款方<input v-model="form.payee" maxlength="200" placeholder="与商家名称不一致时填写" /></label>
              <label class="field">统一社会信用代码<input v-model="form.creditCode" data-field="creditCode" maxlength="30" placeholder="选填，合同或企业信息中可查" @input="markManual('creditCode')" /><small v-if="errors.creditCode" class="field-error">{{ errors.creditCode }}</small></label>
            </div>
          </details>

          <div class="intake-compose-footer">
            <span><AppIcon name="file" :size="16" />创建后可添加证据材料</span>
            <button class="btn btn-primary" :disabled="store.busy || !form.summary.trim()">{{ store.busy ? '正在创建…' : '创建案件，开始梳理' }}<AppIcon name="arrow" :size="17" /></button>
          </div>
        </form>
        <p class="intake-caption">先描述，再补充，一件事对应一个独立的维权记录。</p>
      </div>
    </section>
  </div>
</template>
