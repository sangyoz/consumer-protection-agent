<script setup>
import { stages } from '../domain/case'
defineProps({ stage: String })
</script>
<template><span class="badge" :class="`badge-${stage}`">{{ stages[stage] || stage }}</span></template>
