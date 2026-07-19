/** 地址簿标签：仅 DOM-FOOD / DOM-SHOP / GENERIC 交易壳使用 */

import { getDomain } from './domainSchema.js'

const FOOD_TAGS = ['家', '学校', '公司', '宿舍', '其它']
const SHOP_TAGS = ['家', '公司', '学校', '其它']

export function domainNeedsAddressBook() {
  const d = getDomain()
  return d === 'DOM-FOOD' || d === 'DOM-SHOP' || d === 'DOM-GENERIC'
}

export function addressTagOptions() {
  if (getDomain() === 'DOM-FOOD') return [...FOOD_TAGS]
  return [...SHOP_TAGS]
}

export function normalizeAddressTag(tag) {
  const t = (tag || '').trim()
  return t || '其它'
}
