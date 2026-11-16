<script setup>
import { computed } from 'vue'
import { CHANNELS, MATERIAL_KINDS } from '../../domain/case'
import AppIcon from '../AppIcon.vue'

const props = defineProps({ item: Object })
const uploaded = computed(() => new Set(props.item.materials.map(m => m.kind)))

function missingFor(channel) {
  return channel.materials.filter(kind => !uploaded.value.has(kind))
}
</script>

<template>
  <section class="panel content-panel">
    <div class="panel-title"><h2>其他解决方案</h2><span class="subtle-tag">渠道对照</span></div>
    <p class="body-copy muted">列出常见维权渠道及其受理范围、所需材料；是否适用需结合案情判断，本页不自动推荐渠道。</p>

    <div class="channel-grid">
      <article v-for="channel in CHANNELS" :key="channel.key" class="channel-card">
        <div class="channel-card-head">
          <h3>{{ channel.name }}</h3>
          <em class="tag tag-muted">{{ channel.category }}</em>
        </div>
        <p>{{ channel.scope }}</p>
        <div class="channel-materials">
          <span class="field-caption">通常需要的材料</span>
          <span class="material-tags">
            <em v-for="kind in channel.materials" :key="kind" class="tag" :class="{ 'tag-warn': !uploaded.has(kind) }">{{ MATERIAL_KINDS[kind] }}</em>
          </span>
          <small v-if="missingFor(channel).length" class="small muted">尚缺：{{ missingFor(channel).map(k => MATERIAL_KINDS[k]).join('、') }}</small>
          <small v-else class="small muted gap-ok">所需材料已具备</small>
        </div>
      </article>
    </div>

    <div class="notice-box"><strong>渠道选择说明</strong><p>以上为静态渠道清单；结合纠纷类型、金额和证据情况给出的推荐顺序，后续由 Agent 模块补充。</p></div>
    <RouterLink :to="{ path: '/follow-up', query: { case: item.id } }" class="btn btn-primary">记录新的处理反馈<AppIcon name="arrow" :size="16" /></RouterLink>
  </section>
</template>
