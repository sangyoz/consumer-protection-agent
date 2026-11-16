<script setup>
import { reactive } from 'vue'
import { useCasesStore } from '../stores/cases'

const store = useCasesStore()
let saved = {}
try { saved = JSON.parse(localStorage.getItem('youli.profile.v1') || '{}') || {} } catch { /* 使用空资料 */ }

const form = reactive({ nickname: saved.nickname || '', name: saved.name || '', phone: saved.phone || '', idCard: saved.idCard || '' })
const errors = reactive({ phone: '', idCard: '' })

function maskName(value) {
  if (!value) return ''
  return value.length > 1 ? value[0] + '*'.repeat(value.length - 1) : value
}
function maskTail(value) {
  if (!value) return ''
  return value.length <= 4 ? value : '*'.repeat(value.length - 4) + value.slice(-4)
}

function validate() {
  errors.phone = ''
  errors.idCard = ''
  if (form.phone.trim() && !/^\+?\d[\d\s-]{4,19}$/.test(form.phone.trim())) errors.phone = '请输入有效的联系电话'
  const idCard = form.idCard.trim().toUpperCase()
  if (idCard && !/^\d{17}[\dX]$/.test(idCard)) errors.idCard = '身份证号应为 18 位，末位可为 X'
  return !errors.phone && !errors.idCard
}

function save() {
  if (!validate()) return
  const payload = {
    nickname: form.nickname.trim(),
    name: form.name.trim(),
    phone: form.phone.trim(),
    idCard: form.idCard.trim().toUpperCase(),
  }
  try { localStorage.setItem('youli.profile.v1', JSON.stringify(payload)); store.notify('个人资料已保存到当前浏览器') } catch { store.notify('浏览器存储不可用，资料未保存') }
}
</script>

<template>
  <div class="page profile-page">
    <div class="page-heading"><div><div class="eyebrow">个人中心</div><h1>我的基本资料</h1></div></div>

    <form class="panel content-panel" @submit.prevent="save">
      <div class="profile-intro">
        <span class="avatar large-avatar">{{ form.name ? form.name[0] : '我' }}</span>
        <div>
          <h2>个人工作空间</h2>
          <p class="small muted">资料仅保存在当前浏览器，不会自动对外提交</p>
        </div>
      </div>

      <label class="field">昵称<input v-model="form.nickname" maxlength="50" placeholder="如何称呼你" autocomplete="nickname" /></label>
      <label class="field">姓名<input v-model="form.name" maxlength="30" placeholder="与身份证件一致的姓名" autocomplete="name" /></label>
      <label class="field">联系电话<input v-model="form.phone" maxlength="30" type="tel" placeholder="（选填）" autocomplete="tel" /><small v-if="errors.phone" class="field-error">{{ errors.phone }}</small></label>
      <label class="field">身份证号<input v-model="form.idCard" maxlength="18" placeholder="（选填）" autocomplete="off" /><small v-if="errors.idCard" class="field-error">{{ errors.idCard }}</small></label>

      <div v-if="form.name || form.phone || form.idCard" class="profile-mask-preview">
        <span class="field-caption">脱敏预览</span>
        <p class="small muted">姓名：{{ maskName(form.name) || '未填写' }}　电话：{{ maskTail(form.phone) || '未填写' }}　身份证：{{ maskTail(form.idCard) || '未填写' }}</p>
      </div>

      <div class="notice-box"><strong>资料使用说明</strong><p>当前没有账户认证，也不会自动对外提交个人资料。身份证、平台身份验证等信息在实际需要时再由你确认提供；页面展示时默认脱敏。</p></div>
      <button class="btn btn-primary" type="submit">保存基本资料</button>
    </form>
  </div>
</template>
