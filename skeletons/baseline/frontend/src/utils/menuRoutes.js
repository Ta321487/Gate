/**
 * 菜单 key → 路径（与 backend/app/bake/menu_routes.py 同表）。
 * PortalLayout / AdminLayout / PortalHome 共用，禁止再复制 MENU_TO。
 */

export const USER_MENU_PATHS = {
  home: '/home',
  archive: '/archive',
  my_archive: '/my-archive',
  my_tickets: '/tickets',
  peer_tickets: '/peer-tickets',
  content: '/notices',
  guestbook: '/guestbook',
  ai_assistant: '/ai-assistant',
  exam_papers: '/exam/papers',
  exam_attempts: '/exam/attempts',
  exam_practice: '/exam/practice',
  exam_rank: '/exam/rank',
  exam_wrongbook: '/exam/wrongbook',
  survey_forms: '/survey/forms',
  survey_mine: '/survey/mine',
  vote_campaigns: '/vote/campaigns',
  vote_mine: '/vote/mine',
  doc_browse: '/doc/browse',
  doc_mine: '/doc/mine',
  tb_account: '/tb/account',
  tb_ledger: '/tb/ledger',
  seat_shows: '/seats/shows',
  e_sign_mine: '/e-sign',
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
  ai_knowledge: '/admin/ai-knowledge',
  exam_questions: '/admin/exam/questions',
  exam_papers: '/admin/exam/papers',
  survey_forms: '/admin/survey/forms',
  survey_stats: '/admin/survey/stats',
  vote_candidates: '/admin/vote/candidates',
  vote_results: '/admin/vote/results',
  doc_files: '/admin/doc/files',
  doc_logs: '/admin/doc/logs',
  tb_accounts: '/admin/tb/accounts',
  tb_ledger_admin: '/admin/tb/ledger',
  stock_moves: '/admin/stock/moves',
  stock_ledger: '/admin/stock/ledger',
  e_sign_admin: '/admin/e-sign',
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
