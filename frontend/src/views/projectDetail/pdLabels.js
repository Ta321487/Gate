/** 详情页标签 / 选项常量（纯数据 + 纯函数）。 */
import { JOB_STEP_LABELS } from '../../opsShared'

export const FILL_UNIT_KIND_ZH = {
  island_labels: 'Island 文案',
  island_seeds: '公告种子',
  island_entities: '实体称呼',
  island_roles: '岗位称呼',
  er_labels: 'E-R 中文',
  module_labels: '模块图',
  testcase_labels: '测试用例',
}

export const FILL_UNIT_STATUS_ZH = {
  pending: '待执行',
  running: '进行中',
  done: '完成',
  failed: '失败',
  skipped: '跳过',
}

export const PORTAL_HOME_FALLBACK = [
  { label: '功能卡片首页', value: 'cards' },
  { label: '资讯侧栏首页', value: 'editorial' },
  { label: '商城货架首页', value: 'mall' },
]

export const MALL_PORTAL_HOME_DOMAINS = new Set(['DOM-SHOP', 'DOM-FOOD'])

/** 货架域缺省门户首页为 mall；禁止用 cards 当弱默认盖过商城货架。 */
export function defaultPortalHomeStyle(domain) {
  return MALL_PORTAL_HOME_DOMAINS.has(String(domain || '')) ? 'mall' : 'cards'
}

export const CONTENT_SURFACE_FALLBACK = [
  { label: '刊头阅读流', value: 'folio' },
  { label: '封面墙', value: 'coverwall' },
  { label: '条目清单', value: 'ledger' },
  { label: '双栏阅读台', value: 'splitdesk' },
]

export const CONTENT_SURFACE_DOMAINS = new Set([
  'DOM-MEDIA',
  'DOM-MUSIC',
  'DOM-FORUM',
  'DOM-BLOG',
  'DOM-DOCLIB',
])

export const TRADE_SURFACE_FALLBACK = [
  { label: '货架密铺', value: 'shelfgrid' },
  { label: '档口菜单板', value: 'menuboard' },
  { label: '排片选座行', value: 'showtime' },
]

export const TRADE_SURFACE_DOMAINS = new Set(['DOM-SHOP', 'DOM-FOOD', 'DOM-CINEMA'])

/** 交易隐喻不可乱跨域：排片只影院、档口只餐饮 */
export const TRADE_SURFACE_STYLE_ALLOWED = {
  shelfgrid: new Set(['DOM-SHOP', 'DOM-FOOD', 'DOM-CINEMA']),
  menuboard: new Set(['DOM-FOOD']),
  showtime: new Set(['DOM-CINEMA']),
}

export const RESERVE_SURFACE_FALLBACK = [
  { label: '时段条/号源行', value: 'slotstrip' },
  { label: '房态格', value: 'roomstate' },
  { label: '车型档期卡', value: 'vehiclecard' },
]

export const RESERVE_SURFACE_DOMAINS = new Set([
  'DOM-HOSPITAL',
  'DOM-PARKING',
  'DOM-MEETING',
  'DOM-SALON',
  'DOM-HOTEL',
  'DOM-CARRENT',
  'DOM-INSTRUMENT',
])

/** 房态只酒店、车型只租车/停车 */
export const RESERVE_SURFACE_STYLE_ALLOWED = {
  slotstrip: new Set(['DOM-HOSPITAL', 'DOM-MEETING', 'DOM-SALON', 'DOM-INSTRUMENT']),
  roomstate: new Set(['DOM-HOTEL']),
  vehiclecard: new Set(['DOM-CARRENT', 'DOM-PARKING']),
}

export const BORROW_SURFACE_FALLBACK = [
  { label: '书架脊列', value: 'bookshelf' },
  { label: '库存台账行', value: 'stockrow' },
  { label: '床位色块墙', value: 'bedblocks' },
  { label: '驿站货架格', value: 'parcelshelf' },
]

export const BORROW_SURFACE_DOMAINS = new Set([
  'DOM-LIBRARY',
  'DOM-EQUIP',
  'DOM-ASSET',
  'DOM-PARCEL',
  'DOM-BED',
  'DOM-PROCURE',
])

/** 书架/床位/驿站绑域；台账行留给库存类（图书可作台账备选） */
export const BORROW_SURFACE_STYLE_ALLOWED = {
  bookshelf: new Set(['DOM-LIBRARY']),
  stockrow: new Set(['DOM-ASSET', 'DOM-EQUIP', 'DOM-PROCURE', 'DOM-LIBRARY']),
  bedblocks: new Set(['DOM-BED']),
  parcelshelf: new Set(['DOM-PARCEL']),
}

export const TRADE_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-SHOP': 'shelfgrid',
  'DOM-FOOD': 'menuboard',
  'DOM-CINEMA': 'showtime',
}

export const RESERVE_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-HOSPITAL': 'slotstrip',
  'DOM-MEETING': 'slotstrip',
  'DOM-SALON': 'slotstrip',
  'DOM-INSTRUMENT': 'slotstrip',
  'DOM-HOTEL': 'roomstate',
  'DOM-CARRENT': 'vehiclecard',
  'DOM-PARKING': 'vehiclecard',
}

export const BORROW_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-LIBRARY': 'bookshelf',
  'DOM-ASSET': 'stockrow',
  'DOM-EQUIP': 'stockrow',
  'DOM-PROCURE': 'stockrow',
  'DOM-BED': 'bedblocks',
  'DOM-PARCEL': 'parcelshelf',
}

export const APPLY_SURFACE_FALLBACK = [
  { label: '活动海报墙', value: 'eventposter' },
  { label: '课表网', value: 'coursetable' },
  { label: '启事板', value: 'noticeboard' },
  { label: '线路行程卡', value: 'tourcard' },
]

export const APPLY_SURFACE_DOMAINS = new Set([
  'DOM-ACTIVITY',
  'DOM-COURSE',
  'DOM-LOST',
  'DOM-TOUR',
])

/** 海报/课表/启事/线路一一绑域 */
export const APPLY_SURFACE_STYLE_ALLOWED = {
  eventposter: new Set(['DOM-ACTIVITY']),
  coursetable: new Set(['DOM-COURSE']),
  noticeboard: new Set(['DOM-LOST']),
  tourcard: new Set(['DOM-TOUR']),
}

export const APPLY_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-ACTIVITY': 'eventposter',
  'DOM-COURSE': 'coursetable',
  'DOM-LOST': 'noticeboard',
  'DOM-TOUR': 'tourcard',
}

export const INTERACT_SURFACE_FALLBACK = [
  { label: '资料卡片墙', value: 'profilegrid' },
  { label: '双选志愿卡', value: 'mutualpick' },
  { label: '行程同行行', value: 'triprow' },
]

/** EXAM/SURVEY/VOTE 有专用页，不进本轴 */
export const INTERACT_SURFACE_DOMAINS = new Set([
  'DOM-DATING',
  'DOM-MUTUAL-TUTOR',
  'DOM-MUTUAL-TOPIC',
  'DOM-MUTUAL-TEAM',
  'DOM-CARPOOL',
  'DOM-TIMEBANK',
])

/** 资料墙/双选卡/行程行隐喻绑域 */
export const INTERACT_SURFACE_STYLE_ALLOWED = {
  profilegrid: new Set(['DOM-DATING']),
  mutualpick: new Set(['DOM-MUTUAL-TUTOR', 'DOM-MUTUAL-TOPIC', 'DOM-MUTUAL-TEAM']),
  triprow: new Set(['DOM-CARPOOL', 'DOM-TIMEBANK']),
}

export const INTERACT_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-DATING': 'profilegrid',
  'DOM-MUTUAL-TUTOR': 'mutualpick',
  'DOM-MUTUAL-TOPIC': 'mutualpick',
  'DOM-MUTUAL-TEAM': 'mutualpick',
  'DOM-CARPOOL': 'triprow',
  'DOM-TIMEBANK': 'triprow',
}

export const FOLLOW_SURFACE_FALLBACK = [
  { label: '阶段看板', value: 'pipeline' },
  { label: '档案行+下次跟进', value: 'dossier' },
  { label: '挂牌价签卡', value: 'listing' },
]

export const FOLLOW_SURFACE_DOMAINS = new Set([
  'DOM-CRM',
  'DOM-EVENT',
  'DOM-ATTEND',
  'DOM-FUND',
  'DOM-RECRUIT',
  'DOM-GRADE',
  'DOM-INTERN',
  'DOM-LISTING',
])

/** 阶段看板只客户跟进；挂牌价签只房源；档案行是跟进通用备选 */
export const FOLLOW_SURFACE_STYLE_ALLOWED = {
  pipeline: new Set(['DOM-CRM']),
  listing: new Set(['DOM-LISTING']),
  dossier: new Set([
    'DOM-CRM',
    'DOM-EVENT',
    'DOM-ATTEND',
    'DOM-FUND',
    'DOM-RECRUIT',
    'DOM-GRADE',
    'DOM-INTERN',
    'DOM-LISTING',
  ]),
}

export const FOLLOW_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-CRM': 'pipeline',
  'DOM-LISTING': 'listing',
  'DOM-EVENT': 'dossier',
  'DOM-ATTEND': 'dossier',
  'DOM-FUND': 'dossier',
  'DOM-RECRUIT': 'dossier',
  'DOM-GRADE': 'dossier',
  'DOM-INTERN': 'dossier',
}

export const REPAIR_SURFACE_FALLBACK = [
  { label: '我的工单进度流', value: 'ticketfeed' },
  { label: '分类故障看板', value: 'faultboard' },
]

export const REPAIR_SURFACE_DOMAINS = new Set(['DOM-DORM', 'DOM-PROPERTY', 'DOM-IT'])

/** 两档都是报修隐喻，宿舍/物业/IT 都能手选 */
export const REPAIR_SURFACE_STYLE_ALLOWED = {
  ticketfeed: new Set(['DOM-DORM', 'DOM-PROPERTY', 'DOM-IT']),
  faultboard: new Set(['DOM-DORM', 'DOM-PROPERTY', 'DOM-IT']),
}

export const REPAIR_SURFACE_DOMAIN_DEFAULTS = {
  'DOM-DORM': 'ticketfeed',
  'DOM-PROPERTY': 'ticketfeed',
  'DOM-IT': 'ticketfeed',
}

const APPROVE_DOMAIN_LIST = [
  'DOM-LABSAFE', 'DOM-SEAL', 'DOM-FLEET', 'DOM-CERT', 'DOM-PROMO', 'DOM-FITOUT',
  'DOM-ACAD', 'DOM-TRIP', 'DOM-EXPENSE', 'DOM-CREDIT', 'DOM-LABOR', 'DOM-EVAL',
  'DOM-MORAL', 'DOM-AWARD', 'DOM-PROCURE', 'DOM-CLUB', 'DOM-PROJ', 'DOM-ETHIC',
  'DOM-PARTY', 'DOM-CONTRACT', 'DOM-CARPASS', 'DOM-VISITOR', 'DOM-CHECKIN',
]

export const APPROVE_SURFACE_FALLBACK = [
  { label: '事项类型清单+申请', value: 'typelist' },
  { label: '待审收件箱+步骤条', value: 'inboxsteps' },
]

export const APPROVE_SURFACE_DOMAINS = new Set(APPROVE_DOMAIN_LIST)

/** 两档都是审批隐喻，审批域都能手选 */
export const APPROVE_SURFACE_STYLE_ALLOWED = {
  typelist: new Set(APPROVE_DOMAIN_LIST),
  inboxsteps: new Set(APPROVE_DOMAIN_LIST),
}

export const APPROVE_SURFACE_DOMAIN_DEFAULTS = Object.fromEntries(
  APPROVE_DOMAIN_LIST.map((id) => [id, 'typelist']),
)

export function filterSurfaceOptions(options, allowedMap, domain) {
  if (!domain) return options
  return options.filter((x) => {
    const allowed = allowedMap[x.value]
    return !allowed || allowed.has(domain)
  })
}

export function clampSurfaceStyle(styleId, allowedMap, defaults, domain, fallback) {
  if (!domain || !styleId) return styleId || fallback
  const allowed = allowedMap[styleId]
  if (!allowed || allowed.has(domain)) return styleId
  return defaults[domain] || fallback
}

export const passwordHashOptions = [
  { label: '明文', value: 'none' },
  { label: 'BCrypt', value: 'bcrypt' },
  { label: 'MD5', value: 'md5' },
  { label: 'SHA-256', value: 'sha256' },
]

export const persistenceOptions = [
  { label: 'Spring JDBC（JdbcTemplate）', value: 'jdbc' },
  { label: 'MyBatis + PageHelper', value: 'mybatis' },
  { label: 'Spring Data JPA（Hibernate）', value: 'jpa' },
]

export const securityOptions = [
  { label: '关 · 仅 Session + AdminAuth（默认）', value: 'off' },
  { label: '开 · Spring Security 过滤器链', value: 'on' },
]

export const aiAssistantOptions = [
  { label: '关 · 不出 AI 助手岛（默认）', value: 'off' },
  { label: '开 · Spring AI + DeepSeek + 知识库 FAQ', value: 'on' },
]

export const llmOptions = [
  { label: '开启 · 填充业务文案与种子数据', value: 'on' },
  { label: '关闭 · 仅使用基线生成', value: 'off' },
]

export const planSteps = [
  { t: JOB_STEP_LABELS.parse_merge, m: '匹配与 Spec' },
  { t: JOB_STEP_LABELS.copy_bake, m: '确定性生成' },
  { t: JOB_STEP_LABELS.island_fill, m: '拆解 Unit 并发填岛' },
  { t: JOB_STEP_LABELS.build_verify, m: '编译检查' },
  { t: JOB_STEP_LABELS.gate_e2e, m: '关键路径' },
  { t: JOB_STEP_LABELS.pack, m: '检查通过后打包' },
]

export function persistenceLabel(v) {
  if (v === 'mybatis') return 'MyBatis + PageHelper'
  if (v === 'jpa') return 'Spring Data JPA'
  return 'JdbcTemplate'
}

export function securityLabel(v) {
  const on = v === true || v === 'on' || v === 1
  return on ? 'Spring Security' : 'Session（无过滤器链）'
}

export function securityOn(v) {
  return v === true || v === 'on' || v === 1
}

export function aiAssistantLabel(v) {
  const on = v === true || v === 'on' || v === 1
  return on ? 'AI 助手（Spring AI + DeepSeek）' : '未启用'
}

export function aiAssistantOn(v) {
  return v === true || v === 'on' || v === 1
}

export function warningText(w) {
  return String(w || '').replace(/^提示：/, '')
}

/** 展示名仍含拉丁字母（与后端 looks_latin 对齐；允许 AI/FAQ 等缩写混中文） */
const _ALLOWED_TECH_ACRONYM_RE =
  /(?<![A-Za-z])(?:AI|FAQ|API|ID|URL|OCR|TTS|SMS|QR|JWT|SQL|PPT|LLM|SSE)(?![A-Za-z])/gi

export function labelLooksLatin(text) {
  const stripped = String(text || '').replace(_ALLOWED_TECH_ACRONYM_RE, '')
  return /[A-Za-z]/.test(stripped)
}
