<script setup>
defineProps({ item: Object })
</script>
<template><section class="panel content-panel"><div class="panel-title"><h2>其他解决方案</h2><span class="subtle-tag">扩展模块</span></div><p class="body-copy muted">当协商或投诉尚未解决问题时，在这里结合案件情况补充其他处理建议。</p><div class="strategy-card"><h3>先整理当前处理结果</h3><p>案件：{{ item.title }}</p><p>希望解决：{{ item.goal }}</p></div><div class="inline-empty"><p>后续接入渠道推荐与补充问答</p><span class="small muted">预留消费者协会调解、行业渠道等方案入口，具体建议需结合受理条件。</span></div><RouterLink :to="{ path: '/follow-up', query: { case: item.id } }" class="btn btn-primary">记录新的处理反馈</RouterLink></section></template>
