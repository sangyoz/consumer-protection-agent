import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../stores/auth'
import { dataMode } from '../api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/AuthView.vue'), meta: { title: '登录', public: true } },
    { path: '/register', component: () => import('../views/AuthView.vue'), meta: { title: '注册', public: true } },
    { path: '/', component: () => import('../views/CaseListView.vue'), meta: { title: '案件中心' } },
    { path: '/cases/new', component: () => import('../views/NewCaseView.vue'), meta: { title: '新建案件' } },
    { path: '/cases/:id', component: () => import('../views/WorkbenchView.vue'), meta: { title: '案件工作台' } },
    { path: '/cases/:id/:section(analysis|identity|evidence|calculation|negotiation|platform|complaint|authority|followup|other)', component: () => import('../views/WorkbenchView.vue'), meta: { title: '案件工作台' } },
    { path: '/follow-up', component: () => import('../views/FollowUpView.vue'), meta: { title: '处理跟进' } },
    { path: '/profile', component: () => import('../views/ProfileView.vue'), meta: { title: '个人中心' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.beforeEach(async to => {
  if (dataMode !== 'api') return true
  const user = await useAuth().restore()
  if (!to.meta.public && !user) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.public && user) return '/'
})
export default router
