<script setup>
import { computed, ref, watch } from 'vue'
import { useCasesStore } from '../../stores/cases'
import { api, dataMode } from '../../api'
import { MATERIAL_KINDS, MATERIAL_SOURCES, missingMaterials, shortDate } from '../../domain/case'
import AppIcon from '../AppIcon.vue'

const props = defineProps({ item: Object })
const store = useCasesStore()

const missing = computed(() => missingMaterials(props.item.materials))
const previewUrl = ref('')
const previewName = ref('')

watch(() => props.item?.id, () => { closePreview() })

function formatSize(size) {
  const bytes = Number(size || 0)
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${bytes} B`
}

function isImage(material) {
  return material.kind === 'photo' || /\.(png|jpe?g)$/i.test(material.name || '')
}

async function changeKind(material, event) {
  await store.act('updateMaterialKind', props.item.id, material.id, event.target.value)
}

async function download(material) {
  try {
    const blob = await api.downloadMaterial(props.item.id, material.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = material.name
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    store.notify(err.response?.data?.detail || err.message || '下载失败')
  }
}

async function preview(material) {
  try {
    const blob = await api.downloadMaterial(props.item.id, material.id)
    closePreview()
    previewUrl.value = URL.createObjectURL(blob)
    previewName.value = material.name
  } catch (err) {
    store.notify(err.response?.data?.detail || err.message || '预览失败')
  }
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  previewName.value = ''
}

async function remove(material) {
  if (!window.confirm(`确定删除材料「${material.name}」吗？删除后不可恢复。`)) return
  await store.act('deleteMaterial', props.item.id, material.id)
}
</script>

<template>
  <div class="material-list">
    <div v-for="file in item.materials" :key="file.id" class="evidence-file">
      <AppIcon name="file" :size="17" />
      <div class="evidence-file-body">
        <strong>{{ file.name }}</strong>
        <small>{{ file.status === 'demo' ? '示例材料' : file.status === 'metadata' ? '仅记录名称' : '已上传 · 待解析' }} · {{ formatSize(file.size) }}<template v-if="file.uploadedAt"> · {{ shortDate(file.uploadedAt) }}</template></small>
        <span class="material-tags">
          <em class="tag">{{ MATERIAL_KINDS[file.kind] || MATERIAL_KINDS.other }}</em>
          <em class="tag tag-muted">{{ MATERIAL_SOURCES[file.source] || MATERIAL_SOURCES.user }}</em>
        </span>
        <label class="kind-select">
          <select :value="file.kind" :disabled="item.stage === 'resolved'" @change="changeKind(file, $event)">
            <option v-for="(label, kind) in MATERIAL_KINDS" :key="kind" :value="kind">{{ label }}</option>
          </select>
        </label>
      </div>
      <div class="material-actions">
        <button v-if="isImage(file) && file.storageName" type="button" class="text-link" @click="preview(file)">预览</button>
        <button v-if="file.storageName" type="button" class="text-link" @click="download(file)">下载</button>
        <button v-if="item.stage !== 'resolved'" type="button" class="text-link danger" @click="remove(file)">删除</button>
      </div>
    </div>
    <p v-if="!item.materials.length" class="small muted">可先补充订单或付款凭证。</p>

    <div v-if="missing.length" class="material-gap">
      <span class="field-caption">建议补充的材料</span>
      <ul class="checklist">
        <li v-for="entry in missing" :key="entry.kind"><AppIcon name="file" :size="16" />{{ entry.label }}</li>
      </ul>
    </div>
    <p v-else class="small muted gap-ok">必备材料已齐全，仍可补充合同、宣传页等佐证。</p>
    <p v-if="dataMode === 'mock'" class="fine-print">演示模式只记录文件名、大小和类型，浏览器里没有真实文件，因此不能预览或下载；切换到后端接口模式后才会保存文件内容。</p>

    <div v-if="previewUrl" class="preview-mask" @click="closePreview">
      <img :src="previewUrl" :alt="previewName" @click.stop />
      <button type="button" class="icon-btn preview-close" aria-label="关闭预览" @click="closePreview"><AppIcon name="close" :size="18" /></button>
    </div>
  </div>
</template>
