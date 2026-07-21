import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Home from '../views/Home.vue'
import Profile from '../views/Profile.vue'
import Notices from '../views/Notices.vue'
import NoticeDetail from '../views/NoticeDetail.vue'
import NoticesAdmin from '../views/admin/NoticesAdmin.vue'
import { hasTrait, getSchema, superOnlyAdminPaths } from '../utils/domainSchema.js'

/** 收货地址簿：仅带 addressBook 特征的交易壳，勿挂到酒店预约等 */
function domainNeedsAddressBook() {
  return hasTrait('addressBook')
}
import { adminLoginPath, isSplitEntry, staffLoginPath } from '../utils/authEntry.js'
import {
  clerkAllowedMenuKeys,
  currentStaffPost,
  homePathAfterLogin,
  isWorkerSession,
  workerAllowedPages,
} from '../utils/staffPosts.js'

function portalGuard(_to, _from, next) {
  if (localStorage.getItem('role') !== 'admin') {
    next()
    return
  }
  next(homePathAfterLogin({
    role: 'admin',
    superAdmin: localStorage.getItem('superAdmin') === 'true',
    staffKind: localStorage.getItem('staffKind') || '',
  }))
}

const ADMIN_KEY_BY_PATH = {
  '/admin/dashboard': 'dashboard',
  '/admin/messages': 'messages',
  '/admin/tickets': 'ticket_pending',
  '/admin/ticket-records': 'ticket_records',
  '/admin/overdue': 'deadline',
  '/admin/orders': 'orders',
  '/admin/reservations': 'reservations',
  '/admin/users': 'users',
  '/admin/notices': 'content',
  '/admin/guestbook': 'guestbook',
  '/admin/sites': 'lookup_site',
  '/admin/types': 'lookup_type',
  '/admin/archive': 'archive',
  '/admin/categories': 'category',
  '/admin/profile': 'profile',
}

function adminGuard(to, _from, next) {
  if (localStorage.getItem('role') !== 'admin') {
    next('/')
    return
  }
  if (isWorkerSession()) {
    next('/staff')
    return
  }
  if (superOnlyAdminPaths().has(to.path) && localStorage.getItem('superAdmin') !== 'true') {
    next('/admin/dashboard')
    return
  }
  const allowed = clerkAllowedMenuKeys(currentStaffPost())
  if (allowed && localStorage.getItem('superAdmin') !== 'true') {
    const key = ADMIN_KEY_BY_PATH[to.path]
    if (key && key !== 'profile' && key !== 'messages' && !allowed.has(key)) {
      next('/admin/dashboard')
      return
    }
  }
  next()
}

function staffGuard(to, _from, next) {
  if (localStorage.getItem('role') !== 'admin') {
    next(staffLoginPath())
    return
  }
  if (!isWorkerSession()) {
    next(homePathAfterLogin({
      role: 'admin',
      superAdmin: localStorage.getItem('superAdmin') === 'true',
      staffKind: localStorage.getItem('staffKind') || '',
    }))
    return
  }
  const pages = workerAllowedPages(currentStaffPost())
  const leaf = to.path.replace(/^\/staff\/?/, '') || pages[0] || 'tickets'
  if (pages.length && leaf && !pages.includes(leaf) && to.path !== '/staff') {
    next(`/staff/${pages[0]}`)
    return
  }
  next()
}

const staffRoutes = {
  path: '/staff',
  component: () => import('../layouts/WorkLayout.vue'),
  children: [
    { path: '', redirect: () => {
      const pages = workerAllowedPages(currentStaffPost())
      return `/staff/${pages[0] || 'tickets'}`
    } },
    { path: 'tickets', component: () => import('../views/staff/StaffTickets.vue') },
    { path: 'orders', component: () => import('../views/staff/StaffOrders.vue') },
    { path: 'slots', component: () => import('../views/staff/StaffSlots.vue') },
  ],
  beforeEnter: staffGuard,
}

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

/** 浅拷贝路由树：保留 component / beforeEnter，structuredClone 无法克隆函数会白屏 */
function cloneRoutes(routes) {
  return (routes || []).map((r) => {
    const out = { ...r }
    if (r.meta) out.meta = { ...r.meta }
    if (r.props && typeof r.props === 'object') out.props = { ...r.props }
    if (r.children) out.children = cloneRoutes(r.children)
    return out
  })
}

/** 门户补消息中心；管理端同步挂 /admin/messages */
function withPortalHub(baseRoutes) {
  const routes = cloneRoutes(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const kids = portal?.children
  if (kids) {
    const has = (p) => kids.some((c) => c.path === p)
    if (!has('messages')) {
      const noticeIdx = kids.findIndex((c) => c.path === 'notices')
      const at = noticeIdx >= 0 ? noticeIdx : kids.length
      kids.splice(at, 0, {
        path: 'messages',
        component: () => import('../views/user/Messages.vue'),
      })
    }
  }
  const admin = routes.find((r) => r.path === '/admin')
  const adminKids = admin?.children
  if (adminKids && !adminKids.some((c) => c.path === 'messages')) {
    const dashIdx = adminKids.findIndex((c) => c.path === 'dashboard')
    const at = dashIdx >= 0 ? dashIdx + 1 : 1
    adminKids.splice(at, 0, {
      path: 'messages',
      component: () => import('../views/user/Messages.vue'),
    })
  }
  return routes
}

/** 留言板路由：有 guestbook 能力时挂门户与管理端入口 */
function withGuestbookRoutes(baseRoutes) {
  if (!hasCap('guestbook')) return baseRoutes
  const routes = cloneRoutes(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const kids = portal?.children
  if (kids && !kids.some((c) => c.path === 'guestbook')) {
    const noticeIdx = kids.findIndex((c) => c.path === 'notices')
    const at = noticeIdx >= 0 ? noticeIdx : kids.length
    kids.splice(at, 0, {
      path: 'guestbook',
      component: () => import('../views/Guestbook.vue'),
    })
  }
  const admin = routes.find((r) => r.path === '/admin')
  const adminKids = admin?.children
  if (adminKids && !adminKids.some((c) => c.path === 'guestbook')) {
    const noticeIdx = adminKids.findIndex((c) => c.path === 'notices')
    const at = noticeIdx >= 0 ? noticeIdx : adminKids.length
    adminKids.splice(at, 0, {
      path: 'guestbook',
      component: () => import('../views/admin/GuestbookAdmin.vue'),
    })
  }
  return routes
}

/** 收藏夹：有 favorites 能力时挂门户入口 */
function withFavoritesRoutes(baseRoutes) {
  if (!hasCap('favorites')) return baseRoutes
  const routes = cloneRoutes(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const kids = portal?.children
  if (kids && !kids.some((c) => c.path === 'favorites')) {
    const cartIdx = kids.findIndex((c) => c.path === 'cart')
    const at = cartIdx >= 0 ? cartIdx : kids.length
    kids.splice(at, 0, {
      path: 'favorites',
      component: () => import('../views/user/MyFavorites.vue'),
    })
  }
  return routes
}

/** 浏览历史：有 browse_history 能力时挂门户入口 */
function withBrowseHistoryRoutes(baseRoutes) {
  if (!hasCap('browse_history')) return baseRoutes
  const routes = cloneRoutes(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const kids = portal?.children
  if (kids && !kids.some((c) => c.path === 'browse-history')) {
    const favIdx = kids.findIndex((c) => c.path === 'favorites')
    const at = favIdx >= 0 ? favIdx : kids.length
    kids.splice(at, 0, {
      path: 'browse-history',
      component: () => import('../views/user/BrowseHistory.vue'),
    })
  }
  return routes
}

/** 优惠券：领取 / 我的券 / 管理端 */
function withCouponRoutes(baseRoutes) {
  if (!hasCap('coupon')) return baseRoutes
  const routes = cloneRoutes(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const kids = portal?.children
  if (kids && !kids.some((c) => c.path === 'coupons')) {
    const cartIdx = kids.findIndex((c) => c.path === 'cart')
    const at = cartIdx >= 0 ? cartIdx : kids.length
    kids.splice(at, 0, {
      path: 'coupons',
      component: () => import('../views/user/MyCoupons.vue'),
    })
  }
  const admin = routes.find((r) => r.path === '/admin')
  const adminKids = admin?.children
  if (adminKids && !adminKids.some((c) => c.path === 'coupons')) {
    const ordIdx = adminKids.findIndex((c) => c.path === 'orders')
    const at = ordIdx >= 0 ? ordIdx : adminKids.length
    adminKids.splice(at, 0, {
      path: 'coupons',
      component: () => import('../views/admin/CouponsAdmin.vue'),
    })
  }
  return routes
}

/** 订单评价：用户列表 + 管理端回复 */
function withOrderReviewRoutes(baseRoutes) {
  if (!hasCap('order_review')) return baseRoutes
  const routes = cloneRoutes(baseRoutes)
  const portal = routes.find((r) => r.path === '/')
  const kids = portal?.children
  if (kids && !kids.some((c) => c.path === 'order-reviews')) {
    const ordIdx = kids.findIndex((c) => c.path === 'orders')
    const at = ordIdx >= 0 ? ordIdx + 1 : kids.length
    kids.splice(at, 0, {
      path: 'order-reviews',
      component: () => import('../views/user/MyOrderReviews.vue'),
    })
  }
  const admin = routes.find((r) => r.path === '/admin')
  const adminKids = admin?.children
  if (adminKids && !adminKids.some((c) => c.path === 'order-reviews')) {
    const ordIdx = adminKids.findIndex((c) => c.path === 'orders')
    const at = ordIdx >= 0 ? ordIdx + 1 : adminKids.length
    adminKids.splice(at, 0, {
      path: 'order-reviews',
      component: () => import('../views/admin/OrderReviewsAdmin.vue'),
    })
  }
  return routes
}

/** 在档案+单据壳上追加预约/订单子路由（多主路径，避免再抄一整套 routes） */
function withExtraBizRoutes(baseRoutes, { order = false, slot = false } = {}) {
  const routes = cloneRoutes(baseRoutes)
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
    if (domainNeedsAddressBook() && !has(userKids, 'addresses')) {
      userKids.splice(4, 0, {
        path: 'addresses',
        component: () => import('../views/user/Addresses.vue'),
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
    beforeEnter: portalGuard,
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
    beforeEnter: adminGuard,
  },
  staffRoutes,
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
      { path: 'week', component: () => import('../views/user/WeekCalendar.vue') },
      { path: 'notices', component: Notices },
      { path: 'notices/:id', component: NoticeDetail },
      { path: 'profile', component: Profile },
    ],
    beforeEnter: portalGuard,
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
    beforeEnter: adminGuard,
  },
  staffRoutes,
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
      { path: 'addresses', component: () => import('../views/user/Addresses.vue') },
      { path: 'notices', component: Notices },
      { path: 'notices/:id', component: NoticeDetail },
      { path: 'profile', component: Profile },
    ],
    beforeEnter: portalGuard,
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
    beforeEnter: adminGuard,
  },
  staffRoutes,
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
    beforeEnter: portalGuard,
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
    beforeEnter: adminGuard,
  },
  staffRoutes,
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
    beforeEnter: portalGuard,
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
    beforeEnter: adminGuard,
  },
  staffRoutes,
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
  let routes
  if (ticket && (order || slot)) {
    routes = withPortalHub(withExtraBizRoutes(archiveTicketRoutes, { order, slot }))
  } else if (useArchiveTicketShell()) routes = withPortalHub(archiveTicketRoutes)
  else if (useTicketShell()) routes = withPortalHub(ticketRoutes)
  else if (useOrderShell()) routes = withPortalHub(orderRoutes)
  else if (useSlotShell()) routes = withPortalHub(slotRoutes)
  else if (useArchiveOnlyShell()) routes = withPortalHub(archiveOnlyRoutes)
  else routes = baselineRoutes
  return withOrderReviewRoutes(
    withCouponRoutes(withBrowseHistoryRoutes(withFavoritesRoutes(withGuestbookRoutes(routes)))),
  )
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
  routes: [
    { path: '/admin/login', component: Login, props: { entrySide: 'admin' } },
    { path: '/staff/login', component: Login, props: { entrySide: 'staff' } },
    ...pickRoutes(),
    ...specialRoutes,
  ],
})

const publicPaths = new Set([
  '/login',
  '/admin/login',
  '/staff/login',
  '/register',
  '/error',
  '/loading',
])

function safeRedirect(path) {
  if (!path || typeof path !== 'string') return ''
  if (!path.startsWith('/') || path.startsWith('//')) return ''
  if (path.startsWith('/login') || path.startsWith('/admin/login') || path.startsWith('/staff/login')) {
    return ''
  }
  return path
}

router.beforeEach(async (to, _from, next) => {
  if (publicPaths.has(to.path)) {
    next()
    return
  }
  const token = localStorage.getItem('token')
  const {
    probeSession,
    loginPathForRole,
    isGuestBrowseEnabled,
    isPortalPublicPath,
  } = await import('../utils/session.js')

  if (!token) {
    if (
      isGuestBrowseEnabled()
      && isPortalPublicPath(to.path)
      && !to.path.startsWith('/admin')
      && !to.path.startsWith('/staff')
    ) {
      next()
      return
    }
    if (to.path.startsWith('/admin') && isSplitEntry()) {
      next(adminLoginPath())
      return
    }
    if (to.path.startsWith('/staff') && isSplitEntry()) {
      next(staffLoginPath())
      return
    }
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    })
    return
  }
  // 服务重启后 localStorage 仍有 token，须向服务端确认会话
  const role = localStorage.getItem('role')
  const staffKind = localStorage.getItem('staffKind') || ''
  const ok = await probeSession()
  if (!ok) {
    if (
      isGuestBrowseEnabled()
      && isPortalPublicPath(to.path)
      && !to.path.startsWith('/admin')
      && !to.path.startsWith('/staff')
    ) {
      next()
      return
    }
    next(loginPathForRole(role, staffKind))
    return
  }
  next()
})

export { safeRedirect }
export default router
