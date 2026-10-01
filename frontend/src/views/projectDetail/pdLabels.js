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
