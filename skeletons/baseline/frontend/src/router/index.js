import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Home from '../views/Home.vue'
import Profile from '../views/Profile.vue'
import Notices from '../views/Notices.vue'
import NoticeDetail from '../views/NoticeDetail.vue'
import NoticesAdmin from '../views/admin/NoticesAdmin.vue'
import { getSchema, superOnlyAdminPaths } from '../utils/domainSchema.js'

function hasCap(id) {
  return (getSchema().capabilities || []).includes(id)
}

function useTicketShell() {
  // 报修类：有 ticket_flow、无 archive → 基线单据壳（宿舍/物业/IT）
  return hasCap('ticket_flow') && !hasCap('archive')
}

function useArchiveTicketShell() {
  // 借用类：archive + ticket_flow → 组合壳（设备等组 A）
  return hasCap('ticket_flow') && hasCap('archive')
}

const ticketRoutes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  {
    path: '/',
    component: () => import('../layouts/PortalLayout.vue'),
    children: [
      { path: '', redirect: '/tickets' },
      { path: 'tickets', component: () => import('../views/user/MyTickets.vue') },
      { path: 'notices', component: Notices },
      { path: 'notices/:id', component: NoticeDetail },
      { path: 'profile', component: Profile },
    ],
    beforeEnter: (_to, _from, next) => {
      if (localStorage.getItem('role') === 'admin') next('/admin/dashboard')
      else next()
    },
  },
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/TicketDashboard.vue') },
      { path: 'tickets', component: () => import('../views/admin/TicketsAdmin.vue') },
      { path: 'ticket-records', component: () => import('../views/admin/TicketRecordsAdmin.vue') },
      { path: 'users', component: () => import('../views/admin/UsersAdmin.vue') },
      { path: 'notices', component: NoticesAdmin },
      { path: 'sites', component: () => import('../views/admin/LookupSitesAdmin.vue') },
      { path: 'types', component: () => import('../views/admin/LookupTypesAdmin.vue') },
      { path: 'profile', component: Profile },
    ],
    beforeEnter: (to, _from, next) => {
      if (localStorage.getItem('role') !== 'admin') {
        next('/tickets')
        return
      }
      if (superOnlyAdminPaths().has(to.path) && localStorage.getItem('superAdmin') !== 'true') {
        next('/admin/dashboard')
        return
      }
      next()
    },
  },
]

const archiveTicketRoutes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  {
    path: '/',
    component: () => import('../layouts/PortalLayout.vue'),
    children: [
      { path: '', redirect: '/archive' },
      { path: 'archive', component: () => import('../views/user/ArchiveBrowse.vue') },
      { path: 'tickets', component: () => import('../views/user/MyTickets.vue') },
      { path: 'notices', component: Notices },
      { path: 'notices/:id', component: NoticeDetail },
      { path: 'profile', component: Profile },
    ],
    beforeEnter: (_to, _from, next) => {
      if (localStorage.getItem('role') === 'admin') next('/admin/dashboard')
      else next()
    },
  },
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../views/admin/TicketDashboard.vue') },
      { path: 'archive', component: () => import('../views/admin/ArchiveAdmin.vue') },
      { path: 'categories', component: () => import('../views/admin/CategoriesAdmin.vue') },
      { path: 'tickets', component: () => import('../views/admin/TicketsAdmin.vue') },
      { path: 'ticket-records', component: () => import('../views/admin/TicketRecordsAdmin.vue') },
      { path: 'overdue', component: () => import('../views/admin/OverdueAdmin.vue') },
      { path: 'users', component: () => import('../views/admin/UsersAdmin.vue') },
      { path: 'notices', component: NoticesAdmin },
      { path: 'profile', component: Profile },
    ],
    beforeEnter: (to, _from, next) => {
      if (localStorage.getItem('role') !== 'admin') {
        next('/archive')
        return
      }
      if (superOnlyAdminPaths().has(to.path) && localStorage.getItem('superAdmin') !== 'true') {
        next('/admin/dashboard')
        return
      }
      next()
    },
  },
]

const baselineRoutes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/', component: Home },
  { path: '/profile', component: Profile },
  { path: '/notices', component: Notices },
  { path: '/notices/:id', component: NoticeDetail },
  { path: '/admin/notices', component: NoticesAdmin },
]

function pickRoutes() {
  if (useArchiveTicketShell()) return archiveTicketRoutes
  if (useTicketShell()) return ticketRoutes
  return baselineRoutes
}

/** 领域特化特殊页：文案随 domainFlavor，配色随 data-theme */
const specialRoutes = [
  {
    path: '/error',
    component: () => import('../views/special/SpecialPage.vue'),
    props: { kind: '500' },
  },
  {
    path: '/loading',
    component: () => import('../views/special/SpecialPage.vue'),
    props: { kind: 'loading' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/special/SpecialPage.vue'),
    props: { kind: '404' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [...pickRoutes(), ...specialRoutes],
})

const publicPaths = new Set(['/login', '/register', '/error', '/loading'])

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (!publicPaths.has(to.path) && !token) next('/login')
  else next()
})

export default router
