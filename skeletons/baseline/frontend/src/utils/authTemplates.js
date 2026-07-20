/** 基线登录/注册版式：优先工厂交付配置，其次 .env，交付后固定不变 */

import { APP_DELIVERED } from '../appDelivered.js'

export const AUTH_TEMPLATES = [
  {
    id: 'split',
    label: '双栏书香',
    hint: '左侧品牌色板 + 右侧表单',
  },
  {
    id: 'mirror',
    label: '镜像入口',
    hint: '表单在左，品牌在右',
  },
  {
    id: 'center',
    label: '雾面居中',
    hint: '全屏氛围底 + 居中卡片',
  },
  {
    id: 'ribbon',
    label: '顶栏色带',
    hint: '顶部品牌色带，下方表单',
  },
  {
    id: 'ledge',
    label: '浮台登录',
    hint: '大背景字 + 浮起表单台',
  },
  {
    id: 'folio',
    label: '对开页',
    hint: '竖分割线，编辑式排版',
  },
]

const IDS = new Set(AUTH_TEMPLATES.map((t) => t.id))

/** bake / ZIP 交付固定版式 */
export function pickAuthTemplate() {
  const fromFactory = (APP_DELIVERED?.authTemplate || '').trim()
  if (fromFactory && IDS.has(fromFactory)) return fromFactory
  const fromEnv = (import.meta.env.VITE_AUTH_TEMPLATE || '').trim()
  if (fromEnv && IDS.has(fromEnv)) return fromEnv
  return 'split'
}

export function authTemplateMeta(id) {
  return AUTH_TEMPLATES.find((t) => t.id === id) || AUTH_TEMPLATES[0]
}
