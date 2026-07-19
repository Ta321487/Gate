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
  return hasCap('ticket_flow') && !hasCap('archive')
}

function useArchiveTicketShell() {
  return hasCap('ticket_flow') && hasCap('archive') && !hasCap('order_lines') && !hasCap('slot_reserve')
}

function useOrderShell() {
  return hasCap('order_lines') && hasCap('archive') && !hasCap('ticket_flow') && !hasCap('slot_reserve')
}

function useSlotShell() {
  // TRADE+RESERVE：slotRoutes 已含 orders；允许带 order_lines
  return hasCap('slot_reserve') && hasCap('archive') && !hasCap('ticket_flow')
}

function useArchiveOnlyShell() {
  return hasCap('archive') && !hasCap('ticket_flow') && !hasCap('order_lines') && !hasCap('slot_reserve')
}

/** 在档案+单据壳上追加预约/订单子路由（多主路径，避免再抄一整套 routes） */
function withExtraBizRoutes(baseRoutes, { order = false, slot = false } = {}) {
  const routes = structuredClone(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const admin = routes.find((r) => r.path === '/admin')
  const userKids = portal?.children
  const adminKids = admin?.children
  if (!userKids || !adminKids) return routes

  const has = (kids, p) => kids.some((c) => c.path === p)
  if (slot) {
    if (!has(userKids, 'slots')) {
      userKids.splice(2, 0, {
        path: 'slots',
        component: () => import('../views/user/SlotBook.vue'),
      })
    }
    if (!has(userKids, 'reservations')) {
      userKids.splice(3, 0, {
        path: 'reservations',
        component: () => import('../views/user/MyReservations.vue'),
      })
    }
    if (!has(adminKids, 'reservations')) {
      adminKids.splice(4, 0, {
        path: 'reservations',
        component: () => import('../views/admin/ReservationsAdmin.vue'),
      })
    }
  }
  if (order) {
    if (!has(userKids, 'cart')) {
      userKids.splice(2, 0, {
        path: 'cart',
        component: () => import('../views/user/Cart.vue'),
      })
    }
    if (!has(userKids, 'orders')) {
      userKids.splice(3, 0, {
        path: 'orders',
        component: () => import('../views/user/MyOrders.vue'),
      })
    }
    if (!has(adminKids, 'orders')) {
      adminKids.splice(4, 0, {
        path: 'orders',
        component: () => import('../views/admin/OrdersAdmin.vue'),
      })
    }
  }
  return routes
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

const orderRoutes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  {
    path: '/',
    component: () => import('../layouts/PortalLayout.vue'),
    children: [
      { path: '', redirect: '/archive' },
      { path: 'archive', component: () => import('../views/user/ArchiveBrowse.vue') },
      { path: 'cart', component: () => import('../views/user/Cart.vue') },
      { path: 'orders', component: () => import('../views/user/MyOrders.vue') },
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
      { path: 'orders', component: () => import('../views/admin/OrdersAdmin.vue') },
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

const slotRoutes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  {
    path: '/',
    component: () => import('../layouts/PortalLayout.vue'),
    children: [
      { path: '', redirect: '/archive' },
      { path: 'archive', component: () => import('../views/user/ArchiveBrowse.vue') },
      { path: 'slots', component: () => import('../views/user/SlotBook.vue') },
      { path: 'reservations', component: () => import('../views/user/MyReservations.vue') },
      { path: 'orders', component: () => import('../views/user/MyOrders.vue') },
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
      { path: 'reservations', component: () => import('../views/admin/ReservationsAdmin.vue') },
      { path: 'orders', component: () => import('../views/admin/OrdersAdmin.vue') },
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

const archiveOnlyRoutes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  {
    path: '/',
    component: () => import('../layouts/PortalLayout.vue'),
    children: [
      { path: '', redirect: '/archive' },
      { path: 'archive', component: () => import('../views/user/ArchiveBrowse.vue') },
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
  const ticket = hasCap('ticket_flow') && hasCap('archive')
  const order = hasCap('order_lines') && hasCap('archive')
  const slot = hasCap('slot_reserve') && hasCap('archive')
  // 多主路径：单据壳 + 预约/订单（复用 archiveTicketRoutes，不另写三套）
  if (ticket && (order || slot)) {
    return withExtraBizRoutes(archiveTicketRoutes, { order, slot })
  }
  if (useArchiveTicketShell()) return archiveTicketRoutes
  if (useTicketShell()) return ticketRoutes
  if (useOrderShell()) return orderRoutes
  if (useSlotShell()) return slotRoutes
  if (useArchiveOnlyShell()) return archiveOnlyRoutes
  return baselineRoutes
}

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
