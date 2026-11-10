import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

export const useCasesStore = defineStore('cases', () => {
  const items = ref([])
  const current = ref(null)
  const busy = ref(false)
  const error = ref('')
  const toast = ref('')
  let toastTimer
  function notify(message) { toast.value = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.value = '' }, 3500) }
  async function run(action) {
    busy.value = true; error.value = ''
    try { return await action() } catch (err) { const detail = err.response?.data?.detail; error.value = typeof detail === 'string' ? detail : Array.isArray(detail) ? '输入格式不正确，请检查必填信息和长度。' : err.message || '操作失败，请重试。'; return null } finally { busy.value = false }
  }
  function replace(item) {
    current.value = item
    const index = items.value.findIndex(c => c.id === item.id)
    if (index < 0) items.value.unshift(item); else items.value[index] = item
    return item
  }
  async function list() { return run(async () => { items.value = await api.listCases(); return items.value }) }
  async function load(id) { current.value = null; return run(async () => replace(await api.getCase(id))) }
  async function create(input) { return run(async () => replace(await api.createCase(input))) }
  async function act(method, ...args) { return run(async () => replace(await api[method](...args))) }
  return { items, current, busy, error, toast, notify, list, load, create, act }
})
