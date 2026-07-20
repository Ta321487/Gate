/** 地址簿标签：仅带 addressBook 特征的交易壳使用 */
import { hasTrait } from './domainSchema.js'

const FOOD_TAGS = ['家', '学校', '公司', '宿舍', '其它']
const SHOP_TAGS = ['家', '公司', '学校', '其它']

export function addressBookEnabled() {
  return hasTrait('addressBook')
}

/** @deprecated 用 addressBookEnabled */
export function domainNeedsAddressBook() {
  return addressBookEnabled()
}

export function addressTagOptions() {
  if (hasTrait('food')) return [...FOOD_TAGS]
  return [...SHOP_TAGS]
}

export function normalizeAddressTag(tag) {
  const t = (tag || '').trim()
  return t || '其它'
}
