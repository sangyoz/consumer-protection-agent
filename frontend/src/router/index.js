import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('../views/CaseListView.vue'), meta: { title: '案件中心' } },
    { path: '/cases/new', component: () => import('../views/NewCaseView.vue'), meta: { title: '新建案件' } },
    { path: '/cases/:id', redirect: to => `/cases/${to.params.id}/analysis` },
    { path: '/cases/:id/:section(analysis|negotiation|complaint|other)', component: () => import('../views/WorkbenchView.vue'), meta: { title: '案件工作台' } },
    { path: '/follow-up', component: () => import('../views/FollowUpView.vue'), meta: { title: '处理跟进' } },
    { path: '/profile', component: () => import('../views/ProfileView.vue'), meta: { title: '个人中心' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
