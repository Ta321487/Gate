/**
 * 菜单 key → 路径（与 backend/app/bake/menu_routes.py 同表）。
 * PortalLayout / AdminLayout / PortalHome 共用，禁止再复制 MENU_TO。
 */

export const USER_MENU_PATHS = {
  home: '/home',
  archive: '/archive',
  my_archive: '/my-archive',
  my_tickets: '/tickets',
  content: '/notices',
  guestbook: '/guestbook',
  dm: '/dm',
  profile: '/profile',
  favorites: '/favorites',
  browse_history: '/browse-history',
  coupons: '/coupons',
  cart: '/cart',
  my_orders: '/orders',
  order_reviews: '/order-reviews',
  addresses: '/addresses',
  my_reservations: '/reservations',
  slots: '/slots',
  week_calendar: '/week',
  messages: '/messages',
}

export const ADMIN_MENU_PATHS = {
  dashboard: '/admin/dashboard',
  messages: '/admin/messages',
  ticket_pending: '/admin/tickets',
  ticket_records: '/admin/ticket-records',
  users: '/admin/users',
  content: '/admin/notices',
  guestbook: '/admin/guestbook',
  archive_logs: '/admin/archive-logs',
  lookup_site: '/admin/sites',
  lookup_type: '/admin/types',
  archive: '/admin/archive',
  category: '/admin/categories',
  deadline: '/admin/overdue',
  coupons: '/admin/coupons',
  orders: '/admin/orders',
  order_reviews: '/admin/order-reviews',
  reservations: '/admin/reservations',
}

export function userMenuPath(key) {
  return USER_MENU_PATHS[key] || ''
}

export function adminMenuPath(key) {
  return ADMIN_MENU_PATHS[key] || ''
}
