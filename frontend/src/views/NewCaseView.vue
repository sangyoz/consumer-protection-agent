<script setup>
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useCasesStore } from '../stores/cases'
import AppIcon from '../components/AppIcon.vue'
import StatusBadge from '../components/StatusBadge.vue'
const router = useRouter()
const store = useCasesStore()
const form = reactive({ title: '', summary: '', merchant: '', amount: '', goal: '' })
const examples = [{ title: '网购商品质量问题', text: '我网购的商品收到后无法正常使用，已经联系商家，希望协商退货退款。' }, { title: '预付卡退款纠纷', text: '我购买了会员卡，门店突然停业，剩余服务无法使用，希望退还未消费的费用。' }, { title: '售后处理不及时', text: '商品出现问题后申请售后，商家一直让我等待，没有说明具体处理时间。' }]
onMounted(store.list)
async function submit() {
  if (!form.summary.trim()) return
  const item = await store.create({ ...form, title: form.title.trim() || form.summary.trim().slice(0, 24), summary: form.summary.trim(), amount: Number(form.amount || 0) })
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
      <div class="intake-welcome"><span class="intake-emblem">理</span><div class="eyebrow">有理 · 消费维权助手</div><h1>说说你遇到的问题</h1><p>从发生了什么开始，证据和细节可以慢慢补充。</p><div class="example-list"><button v-for="example in examples" :key="example.title" type="button" class="example-chip" @click="form.summary = example.text">{{ example.title }}<AppIcon name="plus" :size="13" /></button></div></div>
      <div class="intake-composer-area"><div v-if="store.error" class="error-banner" role="alert">{{ store.error }}</div><form class="intake-composer panel" @submit.prevent="submit"><label for="summary" class="field-caption">你遇到了什么消费问题？</label><textarea id="summary" v-model="form.summary" rows="3" maxlength="10000" required placeholder="描述案件的具体情况，例如购买经过、遇到的问题、商家的回复……"></textarea><details class="intake-details"><summary>补充已知信息 <span>选填</span></summary><div class="form-grid"><label class="field">案件标题<input v-model="form.title" maxlength="100" placeholder="便于查找" /></label><label class="field">商家名称<input v-model="form.merchant" maxlength="200" placeholder="合同或订单上的商家名称" /></label><label class="field">交易金额（元）<input v-model="form.amount" type="number" min="0" max="100000000" step="0.01" placeholder="可以留空" /></label><label class="field">希望如何解决<input v-model="form.goal" maxlength="1000" placeholder="例如退货退款、维修" /></label></div></details><div class="intake-compose-footer"><span><AppIcon name="file" :size="16" />创建后可添加证据材料</span><button class="btn btn-primary" :disabled="store.busy || !form.summary.trim()">{{ store.busy ? '正在创建…' : '创建案件，开始梳理' }}<AppIcon name="arrow" :size="17" /></button></div></form><p class="intake-caption">先描述，再补充，一件事对应一个独立的维权记录。</p></div>
    </section>
  </div>
</template>
