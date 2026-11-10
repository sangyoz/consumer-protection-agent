<script setup>
import { reactive } from 'vue'
import { useCasesStore } from '../stores/cases'
const store = useCasesStore()
let saved = {}
try { saved = JSON.parse(localStorage.getItem('youli.profile.v1') || '{}') || {} } catch { /* 使用空资料 */ }
const form = reactive({ nickname: saved.nickname || '', phone: saved.phone || '' })
function save() { try { localStorage.setItem('youli.profile.v1', JSON.stringify(form)); store.notify('个人资料已保存到当前浏览器') } catch { store.notify('浏览器存储不可用，资料未保存') } }
</script>
<template><div class="page profile-page"><div class="page-heading"><div><div class="eyebrow">个人中心</div><h1>我的基本资料</h1><p>先保留必要信息，后续按投诉渠道要求补充。</p></div></div><form class="panel content-panel" @submit.prevent="save"><div class="profile-intro"><span class="avatar large-avatar">我</span><div><h2>个人工作空间</h2><p class="small muted">资料仅保存在当前浏览器</p></div></div><label class="field">昵称<input v-model="form.nickname" maxlength="50" placeholder="如何称呼你" autocomplete="nickname" /></label><label class="field">联系电话（选填）<input v-model="form.phone" maxlength="30" type="tel" placeholder="需要投诉时再补充也可以" autocomplete="tel" /></label><div class="notice-box"><strong>资料使用说明</strong><p>当前没有账户认证，也不会自动对外提交个人资料。身份证、平台身份验证等信息在实际需要时再由用户确认提供。</p></div><button class="btn btn-primary" type="submit">保存基本资料</button></form></div></template>
