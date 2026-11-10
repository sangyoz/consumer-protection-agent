<script setup>
import { useCasesStore } from '../../stores/cases'
import AppIcon from '../AppIcon.vue'
const props = defineProps({ item: Object })
const store = useCasesStore()
async function generate() { if (await store.act('generateComplaint', props.item.id)) store.notify('投诉草稿已生成，尚未对外提交') }
async function copy() { try { await navigator.clipboard.writeText(props.item.complaint); store.notify('投诉草稿已复制') } catch { store.notify('复制失败，请手动选择草稿文本') } }
</script>
<template>
  <section class="panel content-panel"><div class="panel-title"><h2>投诉材料准备</h2><span class="subtle-tag">用户核对后提交</span></div><p class="muted body-copy">复用本案的事实、诉求和沟通记录，整理投诉材料。</p><div class="evidence-checks"><div><AppIcon :name="item.merchant ? 'check' : 'file'" :size="17" /><span>投诉对象与经营主体</span><span class="small muted">{{ item.merchant ? '已录入，待核实' : '待补充' }}</span></div><div><AppIcon :name="item.materials.length ? 'check' : 'file'" :size="17" /><span>订单、合同及付款凭证</span><span class="small muted">{{ item.materials.length }} 份材料，待核对</span></div><div><AppIcon :name="item.messages.length ? 'check' : 'file'" :size="17" /><span>与商家的沟通记录</span><span class="small muted">{{ item.messages.filter(m => m.role === 'merchant').length }} 条商家回复</span></div></div><div class="panel-title"><h3>投诉内容预览</h3><button v-if="item.complaint" class="text-link" @click="copy"><AppIcon name="copy" :size="15" />复制草稿</button></div><pre v-if="item.complaint" class="complaint-preview">{{ item.complaint }}</pre><div v-else class="inline-empty"><AppIcon name="file" :size="30" /><p>还没有投诉草稿</p><span class="small muted">点击下方按钮，根据当前案件信息整理。</span></div><div class="panel-actions"><button class="btn btn-primary" :disabled="store.busy || item.stage === 'resolved'" @click="generate">{{ store.busy ? '正在整理…' : item.complaint ? '重新生成草稿' : '生成投诉材料' }}</button><RouterLink :to="{ path: '/follow-up', query: { case: item.id } }" class="btn btn-secondary">记录处理进度<AppIcon name="arrow" :size="16" /></RouterLink></div><div class="notice-box"><strong>下一步由你确认</strong><p>全国 12315、交易平台售后等渠道需结合案件选择。本框架仅整理材料，不会向外部平台提交；辅助填表留待后续接入。</p></div></section>
</template>
