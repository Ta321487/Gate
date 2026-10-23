/**
 * 冒烟专用：把 APP_DELIVERED 包成 Proxy，读 window.__LAYOUT_SMOKE_DELIVERED__ 覆盖皮字段。
 * 不改 skeletons 业务源；仅 vite.smoke 管道挂载。
 */
export function layoutSmokeDeliveredProxy() {
  return {
    name: 'layout-smoke-delivered-proxy',
    enforce: 'pre',
    transform(code, id) {
      const norm = String(id || '').replace(/\\/g, '/')
      if (!norm.endsWith('/frontend/src/appDelivered.js')) return null
      if (!code.includes('export const APP_DELIVERED')) return null
      const next =
        code.replace(
          'export const APP_DELIVERED =',
          'const __LAYOUT_SMOKE_BASE__ =',
        ) +
        `
export const APP_DELIVERED = new Proxy(__LAYOUT_SMOKE_BASE__, {
  get(target, prop, receiver) {
    try {
      const o = globalThis.__LAYOUT_SMOKE_DELIVERED__
      if (o && Object.prototype.hasOwnProperty.call(o, prop)) return o[prop]
    } catch (_) {}
    return Reflect.get(target, prop, receiver)
  },
})
`
      return { code: next, map: null }
    },
  }
}
