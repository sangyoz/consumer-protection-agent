<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCasesStore } from '../stores/cases'
import { money, sections, steps, stageStep } from '../domain/case'
import { dataMode } from '../api'
import AppIcon from '../components/AppIcon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import AnalysisPanel from '../components/workbench/AnalysisPanel.vue'
import NegotiationPanel from '../components/workbench/NegotiationPanel.vue'
import NegotiationAdvice from '../components/workbench/NegotiationAdvice.vue'
import ComplaintPanel from '../components/workbench/ComplaintPanel.vue'
import OtherPanel from '../components/workbench/OtherPanel.vue'

const route = useRoute()
const store = useCasesStore()
const leftOpen = ref(true)
const rightOpen = ref(true)
const item = computed(() => store.current)
const activeIndex = computed(() => sections.findIndex(s => s.key === route.params.section))
const panel = computed(() => ({ analysis: AnalysisPanel, negotiation: NegotiationPanel, complaint: ComplaintPanel, other: OtherPanel })[route.params.section])
watch(() => route.params.id, id => store.load(id), { immediate: true })
async function upload(event) {
  const files = [...event.target.files]
  event.target.value = ''
  if (!files.length) return
  const allowed = /\.(pdf|docx|png|jpe?g|txt)$/i
  if (files.length > 5 || files.some(f => f.size > 10 * 1024 * 1024 || !allowed.test(f.name))) { store.notify('每次最多 5 份，单份不超过 10 MB，支持 PDF、DOCX、图片和 TXT'); return }
  if (await store.act('addMaterials', item.value.id, files)) store.notify(dataMode === 'mock' ? '已记录附件名称；演示模式不保存文件内容' : '附件已保存，内容解析尚未接入')
}
</script>

<template>
  <div class="case-workspace">
    <div v-if="store.error" class="error-banner" role="alert">{{ store.error }}<button class="text-link" @click="store.load(route.params.id)">重新加载案件</button></div>
    <div v-if="!item" class="empty-state panel">{{ store.busy ? '正在加载案件…' : '暂时无法打开案件，请重试或返回案件中心。' }}</div>
    <template v-else>
      <header class="workspace-heading"><div><span class="eyebrow">当前案件</span><h1>{{ item.title }}</h1></div><StatusBadge :stage="item.stage" /></header>
      <div class="workbench-toolbar"><nav class="workbench-tabs" aria-label="案件阶段"><RouterLink v-for="(section, index) in sections" :key="section.key" :to="`/cases/${item.id}/${section.key}`" :class="{ active: section.key === route.params.section }"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ section.label }}</RouterLink></nav><div class="fold-buttons"><button class="icon-btn" :aria-pressed="leftOpen" :aria-label="leftOpen ? '收起案件信息' : '展开案件信息'" @click="leftOpen = !leftOpen"><AppIcon name="file" :size="17" /></button><button class="icon-btn" :aria-pressed="rightOpen" :aria-label="rightOpen ? '收起处理进度' : '展开处理进度'" @click="rightOpen = !rightOpen"><AppIcon name="clock" :size="17" /></button></div></div>
      <div v-if="item.stage === 'resolved'" class="notice-box resolved-notice">本案已确认解决。历史材料与沟通记录可继续查看；如有新问题，可在“处理跟进”中记录并重新进入处理阶段。</div>
      <div class="workspace-layout" :class="{ 'hide-left': !leftOpen, 'hide-right': !rightOpen }">
        <aside v-if="leftOpen" class="panel case-context">
          <div class="panel-title"><h2>案件基本信息</h2><button class="icon-btn" aria-label="收起案件信息" @click="leftOpen = false"><AppIcon name="close" :size="15" /></button></div>
          <dl class="case-facts"><dt>商家名称</dt><dd>{{ item.merchant || '待补充' }}</dd><dt>交易金额</dt><dd class="amount-text">{{ item.amount ? money(item.amount) : '待补充' }}</dd><dt>当前诉求</dt><dd>{{ item.goal }}</dd><dt>事件描述</dt><dd>{{ item.summary }}</dd></dl>
          <div class="divider"></div>
          <div class="panel-title"><h3>用户提供的证据信息</h3><span class="small muted">{{ item.materials.length }} 份</span></div>
          <div v-for="file in item.materials" :key="file.id" class="evidence-file"><AppIcon name="file" :size="17" /><div><strong>{{ file.name }}</strong><small>{{ file.status === 'demo' ? '示例材料' : file.status === 'metadata' ? '仅记录名称' : '已上传 · 待解析' }}</small></div></div>
          <p v-if="!item.materials.length" class="small muted">可先补充订单或付款凭证。</p>
          <label class="upload-btn" :class="{ disabled: store.busy || item.stage === 'resolved' }"><AppIcon name="upload" :size="16" />添加材料<input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg,.txt" multiple :disabled="store.busy || item.stage === 'resolved'" @change="upload" /></label>
          <p class="fine-print">单份不超过 10 MB。{{ dataMode === 'mock' ? '演示模式仅记录文件名。' : '已上传文件的解析能力待接入。' }}</p>
        </aside>
        <div class="workspace-center"><component :is="panel" :item="item" :key="item.id + route.params.section" /></div>
        <aside v-if="rightOpen" class="panel workspace-right">
          <div class="panel-title"><h2>处理进度</h2><button class="icon-btn" aria-label="收起处理进度" @click="rightOpen = false"><AppIcon name="close" :size="15" /></button></div>
          <ol class="compact-progress"><li v-for="(step, index) in steps" :key="step" :class="{ done: index < stageStep[item.stage], current: index === stageStep[item.stage] }"><span class="compact-step"><AppIcon v-if="index < stageStep[item.stage]" name="check" :size="12" /><span v-else>{{ index + 1 }}</span></span><span>{{ step }}</span></li></ol>
          <div class="workspace-right-body">
            <NegotiationAdvice v-if="route.params.section === 'negotiation'" :item="item" :key="item.id" />
            <section v-else class="stage-guide"><h2>{{ route.params.section === 'analysis' ? '先把事实和诉求梳理清楚' : route.params.section === 'complaint' ? '先核对材料，再选择渠道' : '根据反馈调整下一步' }}</h2><p>{{ route.params.section === 'analysis' ? '先核对商家、订单、交易金额和现有证据，再明确希望解决的问题。' : route.params.section === 'complaint' ? '投诉内容应基于已提供的事实。核对经营主体、诉求和附件后，由你确认提交。' : '记录已经尝试的方式和新反馈，再决定是否继续协商或寻求其他帮助。' }}</p><div class="notice-box"><strong>下一步由你决定</strong><p>页面切换不会自动提交投诉或接受方案。实际履行完成后，再确认结案。</p></div></section>
          </div>
          <footer class="workspace-right-footer"><div class="step-actions"><RouterLink v-if="activeIndex > 0" :to="`/cases/${item.id}/${sections[activeIndex - 1].key}`" class="btn btn-secondary">上一步</RouterLink><RouterLink v-if="activeIndex < sections.length - 1" :to="`/cases/${item.id}/${sections[activeIndex + 1].key}`" class="btn btn-primary">下一步<AppIcon name="arrow" :size="14" /></RouterLink></div><RouterLink :to="{ path: '/follow-up', query: { case: item.id } }" class="text-link progress-link">记录处理进度<AppIcon name="arrow" :size="15" /></RouterLink></footer>
        </aside>
      </div>
    </template>
  </div>
</template>
