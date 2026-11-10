<script setup>
import { nextTick, ref } from 'vue'
import { useCasesStore } from '../../stores/cases'
import AppIcon from '../AppIcon.vue'
const props = defineProps({ item: Object })
const store = useCasesStore()
const input = ref('')
const chat = ref(null)
async function send() {
  const content = input.value.trim()
  if (!content) return
  if (await store.act('sendMessage', props.item.id, content)) { input.value = ''; await nextTick(); chat.value?.scrollTo({ top: chat.value.scrollHeight, behavior: 'smooth' }) }
}
</script>

<template>
  <section class="panel chat-panel negotiation-chat"><div class="panel-title"><h2>与商家的沟通记录</h2><span class="subtle-tag">模拟对话</span></div><div ref="chat" class="chat-history" aria-live="polite"><div class="chat-date">案件上下文会保留在本次沟通中</div><div v-if="!item.messages.length" class="inline-empty"><AppIcon name="chat" :size="30" /><p>还没有沟通记录</p><span class="small muted">参考右侧建议与商家沟通，再粘贴对方的回复。</span></div><div v-for="message in item.messages" :key="message.id" class="message" :class="`message-${message.role}`"><span class="message-label">{{ message.role === 'merchant' ? '商家回复 · 用户录入' : '有理 · 演示分析' }}</span><p>{{ message.content }}</p></div></div><form class="chat-compose" @submit.prevent="send"><label for="merchant-reply" class="field-caption">粘贴商家的最新回复</label><textarea id="merchant-reply" v-model="input" rows="3" maxlength="10000" placeholder="例如：退款需要等待公司统一处理，请耐心等待……" :disabled="item.stage === 'resolved'"></textarea><div class="compose-footer"><span class="small muted">保留上下文，逐轮调整策略</span><button class="btn btn-primary" :disabled="store.busy || !input.trim() || item.stage === 'resolved'">{{ store.busy ? '正在分析…' : '分析这条回复' }}<AppIcon name="arrow" :size="15" /></button></div></form></section>
</template>
