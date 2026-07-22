/**
 * 收藏 / 足迹 / 购物车等接口封装。
 */
import http from '../api/http.js'

export function toggleFavorite(itemId) {
  const id = Number(itemId)
  return http.post(`/api/favorites/${id}/toggle`)
}

export function touchBrowseHistory(itemId) {
  const id = Number(itemId)
  return http.post(`/api/browse-history/${id}`)
}

export function upsertCart(itemId, qty = 1) {
  const id = Number(itemId)
  const n = Number(qty) || 1
  return http.post('/api/cart', { itemId: id, qty: n })
}

export function removeCart(itemId) {
  const id = Number(itemId)
  return http.post('/api/cart/remove', { itemId: id })
}
