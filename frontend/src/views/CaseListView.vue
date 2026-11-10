<script setup>
import { computed, onMounted, ref } from 'vue'
import { useCasesStore } from '../stores/cases'
import { money, shortDate, stageStep, steps } from '../domain/case'
import StatusBadge from '../components/StatusBadge.vue'
import AppIcon from '../components/AppIcon.vue'
const store = useCasesStore()
const search = ref('')
const filter = ref('all')
const openCount = computed(() => store.items.filter(c => c.stage !== 'resolved').length)
const filtered = computed(() => store.items.filter(c => (filter.value === 'all' || (filter.value === 'resolved' ? c.stage === 'resolved' : c.stage !== 'resolved')) && `${c.title}${c.summary}`.includes(search.value.trim())))
onMounted(store.list)
</script>

<template>
  <div class="page">
    <div class="page-heading"><div><div class="eyebrow">我的维权工作空间</div><h1>把消费纠纷，一步步解决</h1><p>从梳理事实到跟进结果，每一个案件都在这里。</p></div><RouterLink to="/cases/new" class="btn btn-primary"><AppIcon name="plus" :size="18" />新建案件</RouterLink></div>
    <section class="welcome-strip"><span class="welcome-icon"><AppIcon name="shield" :size="28" /></span><div><h2>先说说发生了什么</h2><p>不必准备好所有材料。描述你的问题，我们再一起补充。</p></div><RouterLink to="/cases/new" class="text-link">开始梳理<AppIcon name="arrow" :size="17" /></RouterLink></section>
    <div class="section-toolbar"><div class="filter-tabs" role="group" aria-label="筛选案件"><button :class="{ active: filter === 'all' }" @click="filter = 'all'">全部案件 <span>{{ store.items.length }}</span></button><button :class="{ active: filter === 'open' }" @click="filter = 'open'">处理中 <span>{{ openCount }}</span></button><button :class="{ active: filter === 'resolved' }" @click="filter = 'resolved'">已解决</button></div><label class="search-box"><AppIcon name="search" :size="17" /><input v-model="search" placeholder="搜索案件" aria-label="搜索案件" /></label></div>
    <div v-if="store.error" class="error-banner" role="alert">{{ store.error }}<button class="text-link" @click="store.list">重新加载</button></div>
    <div v-if="store.busy" class="empty-state">正在加载案件…</div>
    <div v-else-if="!filtered.length" class="empty-state panel"><AppIcon name="file" :size="34" /><h2>{{ search || filter !== 'all' ? '没有符合条件的案件' : '从第一个案件开始' }}</h2><p>你可以调整筛选条件，或新建一个维权案件。</p><RouterLink to="/cases/new" class="btn btn-primary">新建案件</RouterLink></div>
    <div v-else class="case-list-layout"><RouterLink v-for="item in filtered" :key="item.id" :to="`/cases/${item.id}/${item.stage === 'negotiating' ? 'negotiation' : item.stage === 'complaining' ? 'complaint' : 'analysis'}`" class="case-card panel"><span class="case-symbol"><AppIcon name="file" :size="22" /></span><div class="case-row-content"><h2>{{ item.title }}</h2><p class="case-excerpt">{{ item.summary }}</p><div class="case-row-meta"><span>{{ item.merchant || '商家信息待补充' }}</span><strong>{{ item.amount ? money(item.amount) : '金额待补充' }}</strong><span>{{ shortDate(item.updatedAt) }} 更新</span></div></div><div class="case-row-progress"><StatusBadge :stage="item.stage" /><div class="case-stage-track" aria-hidden="true"><i v-for="(_, index) in steps" :key="index" :class="{ reached: index <= stageStep[item.stage] }"></i></div><span class="text-link">继续处理<AppIcon name="arrow" :size="16" /></span></div></RouterLink><RouterLink to="/cases/new" class="new-case-row"><AppIcon name="plus" :size="19" />新建一个维权案件</RouterLink></div>
    <div class="page-footnote"><AppIcon name="shield" :size="15" />目前为框架演示，分析结果及法律检索尚未接入真实 AI 服务。</div>
  </div>
</template>
