import { ref } from 'vue'
import axios from 'axios'

const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api', withCredentials: true })
const user = ref(null)
let loaded = false
export function useAuth() {
  async function restore() {
    if (loaded) return user.value
    try { user.value = (await client.get('/auth/me')).data } catch { user.value = null }
    loaded = true
    return user.value
  }
  async function submit(mode, credentials) {
    user.value = (await client.post(`/auth/${mode}`, credentials)).data
    loaded = true
    return user.value
  }
  async function logout() {
    await client.post('/auth/logout')
    user.value = null
    loaded = true
  }
  function invalidate() { user.value = null; loaded = true }
  return { user, restore, submit, logout, invalidate }
}
