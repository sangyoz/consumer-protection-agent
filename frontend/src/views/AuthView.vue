<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { useCasesStore } from '../stores/cases'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const cases = useCasesStore()
const register = computed(() => route.path === '/register')
const username = ref('')
const password = ref('')
const confirm = ref('')
const visible = ref(false)
const busy = ref(false)
const error = ref('')
watch(() => route.path, () => { error.value = ''; password.value = ''; confirm.value = '' })
async function submit() {
  error.value = ''
  if (register.value && password.value !== confirm.value) { error.value = '两次输入的密码不一致'; return }
  busy.value = true
  try {
    await auth.submit(register.value ? 'register' : 'login', { username: username.value.trim(), password: password.value })
    cases.items = []; cases.current = null; cases.error = ''; cases.toast = ''
    const next = route.query.redirect
    await router.replace(typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') && !/^\/(login|register)/.test(next) ? next : '/')
  } catch (err) {
    const detail = err.response?.data?.detail
    error.value = err.response?.status === 404
      ? '账号接口不存在，请更新并重启后端，检查前端是否连接了正确的服务'
      : typeof detail === 'string' ? detail : Array.isArray(detail) ? '请检查账号格式和密码长度' : '暂时无法连接，请确认服务已启动'
  } finally { busy.value = false }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-story">
      <div class="brand"><span class="brand-mark">理</span><span><strong>有理</strong><small>消费维权助手</small></span></div>
      <div class="auth-story-content"><span class="auth-eyebrow">让每一步，都有依据</span><h1>把事情说清楚，<br />把权益找回来。</h1><p>从梳理案情到理性协商，<br />你的维权进展，都在自己的工作空间。</p>
        <div class="auth-case-note"><AppIcon name="shield" :size="24" /><div><strong>留住证据，也留住每一步进展</strong><span>案件、材料与沟通记录，登录后继续处理。</span></div></div>
      </div><small class="muted">有理 · 个人消费维权工作空间</small>
    </section>
    <section class="auth-form-region">
      <form class="auth-form" @submit.prevent="submit">
        <div class="eyebrow">{{ register ? '创建你的工作空间' : '欢迎回来' }}</div>
        <h2>{{ register ? '注册有理账号' : '登录有理' }}</h2>
        <p class="muted">{{ register ? '保存案件与处理进度，随时继续维权。' : '继续查看你的案件与处理进度。' }}</p>
        <label class="field">账号<input v-model="username" required minlength="3" maxlength="32" pattern="[A-Za-z0-9_]{3,32}" autocomplete="username" placeholder="输入账号" :disabled="busy" /><small class="muted">3–32 位英文字母、数字或下划线，不区分大小写</small></label>
        <label class="field">密码<input v-model="password" :type="visible ? 'text' : 'password'" required minlength="8" maxlength="128" :autocomplete="register ? 'new-password' : 'current-password'" placeholder="输入至少 8 位密码" :disabled="busy" /></label>
        <label v-if="register" class="field">确认密码<input v-model="confirm" :type="visible ? 'text' : 'password'" required minlength="8" maxlength="128" autocomplete="new-password" placeholder="再次输入密码" :disabled="busy" /></label>
        <label class="auth-show-password"><input v-model="visible" type="checkbox" />显示密码</label>
        <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
        <button class="btn btn-primary auth-submit" :disabled="busy">{{ busy ? '请稍候…' : register ? '注册并进入' : '登录' }}</button>
        <p class="auth-switch">{{ register ? '已有账号？' : '还没有账号？' }} <RouterLink :to="{ path: register ? '/login' : '/register', query: route.query }">{{ register ? '去登录' : '注册账号' }}</RouterLink></p>
      </form>
    </section>
  </main>
</template>

<style scoped>
.auth-page{min-height:100dvh;display:grid;grid-template-columns:1.05fr 1fr;background:var(--surface)}
.auth-story{background:var(--brand-soft);padding:48px clamp(28px,5vw,88px);display:flex;flex-direction:column;justify-content:space-between;gap:48px}
.auth-story-content{padding:40px 0}.auth-eyebrow{color:var(--brand-ink);font-size:14px;letter-spacing:2px}.auth-story h1{font-family:var(--font-title);font-size:clamp(32px,3.4vw,50px);line-height:1.6;margin:20px 0}.auth-story p{color:var(--muted);line-height:2;font-size:16px}
.auth-case-note{display:flex;gap:14px;border-top:1px solid #cce8d6;padding-top:26px;margin-top:42px;color:var(--brand-ink)}.auth-case-note strong,.auth-case-note span{display:block}.auth-case-note span{font-size:13px;color:var(--muted);margin-top:8px}
.auth-form-region{display:flex;align-items:center;justify-content:center;padding:40px 24px}.auth-form{width:min(100%,390px)}.auth-form h2{font-family:var(--font-title);font-size:30px;margin:12px 0}.auth-form>p.muted{margin-bottom:32px}.auth-form .field{margin-top:20px}.auth-form .field input{width:100%}.auth-form .field small{font-size:12px;line-height:1.6;font-weight:400}.auth-show-password{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);margin:16px 0 24px}.auth-submit{width:100%;justify-content:center;min-height:46px}.auth-switch{text-align:center;font-size:14px;color:var(--muted);margin-top:24px}.auth-switch a{color:var(--brand-ink);font-weight:600}.auth-error{color:var(--danger);font-size:14px;background:#fff1f1;padding:12px;border-radius:var(--radius)}
@media(max-width:760px){.auth-page{grid-template-columns:1fr}.auth-story{padding:24px;gap:0}.auth-story-content{padding:20px 0 0}.auth-story h1{font-size:28px;margin:10px 0}.auth-story p,.auth-case-note,.auth-story>small,.auth-eyebrow{display:none}.auth-form-region{padding:30px 24px 48px;align-items:start}}
</style>
