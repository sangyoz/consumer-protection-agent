<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from './components/AppIcon.vue'
import { useCasesStore } from './stores/cases'
import { dataMode } from './api'
const route = useRoute()
const store = useCasesStore()
const menuOpen = ref(false)
const focused = computed(() => route.path.startsWith('/cases/'))
watch(() => route.path, () => { menuOpen.value = false })
const nav = [{ to: '/', icon: 'grid', text: '案件中心' }, { to: '/follow-up', icon: 'clock', text: '处理跟进' }, { to: '/profile', icon: 'user', text: '个人中心' }]
</script>

<template>
  <div class="app-shell" :class="{ 'focused-shell': focused }">
    <aside v-if="!focused" class="sidebar" :class="{ 'is-open': menuOpen }">
      <RouterLink to="/" class="brand" @click="menuOpen = false"><span class="brand-mark">理</span><span><strong>有理</strong><small>消费维权助手</small></span></RouterLink>
      <RouterLink to="/cases/new" class="btn btn-primary sidebar-create" @click="menuOpen = false"><AppIcon name="plus" :size="18" />新建维权案件</RouterLink>
      <div class="nav-label">我的工作空间</div>
      <nav class="nav-list" aria-label="主导航">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" :class="{ selected: item.to === '/' ? route.path === '/' || route.path.startsWith('/cases') : route.path === item.to }" @click="menuOpen = false"><AppIcon :name="item.icon" :size="19" />{{ item.text }}<AppIcon class="nav-arrow" name="chevron" :size="14" /></RouterLink>
      </nav>
      <div class="sidebar-note"><AppIcon name="shield" :size="22" /><strong>让每一步，都有依据</strong><p>梳理事实、理性沟通，<br />一起把问题逐步解决。</p><span>演示数据 · 不会对外发送</span></div>
      <RouterLink to="/profile" class="sidebar-user"><span class="avatar">我</span><span><strong>我的工作空间</strong><small>个人消费维权</small></span><AppIcon name="chevron" :size="15" /></RouterLink>
    </aside>
    <button v-if="menuOpen && !focused" class="sidebar-overlay" aria-label="关闭导航" @click="menuOpen = false"></button>
    <main class="app-main">
      <header class="topbar"><div class="breadcrumb"><RouterLink v-if="focused" to="/" class="focus-brand" aria-label="返回案件中心"><span class="brand-mark">理</span><strong>有理</strong></RouterLink><button v-else class="icon-btn mobile-menu" aria-label="打开导航" @click="menuOpen = !menuOpen"><AppIcon name="menu" /></button><span v-if="!focused">工作空间</span><span class="breadcrumb-slash">/</span><strong>{{ route.meta.title }}</strong></div><div class="topbar-right"><RouterLink v-if="focused" to="/" class="text-link focus-home"><AppIcon name="back" :size="14" />案件中心</RouterLink><span class="environment"><i></i>{{ dataMode === 'mock' ? '本地演示模式' : '后端接口模式' }}</span><RouterLink to="/profile" class="avatar" aria-label="个人中心">我</RouterLink></div></header>
      <RouterView />
      <div v-if="store.toast" class="toast" role="status"><AppIcon name="check" :size="17" />{{ store.toast }}</div>
    </main>
  </div>
</template>
