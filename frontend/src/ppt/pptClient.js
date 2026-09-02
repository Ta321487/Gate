/**
 * 答辩 PPT API 客户端：真实路径优先；404/501 或 VITE_PPT_MOCK=1 时降级 mock。
 * 后端全部完成后须移除 mock 降级（见 docs/defense-ppt-backend.md §1.4）。
 */
import { api } from '../api.js'
import { mockPptApi } from './mockPptApi.js'

const FORCE_ENV = String(import.meta.env.VITE_PPT_MOCK || '') === '1'
let useMock = FORCE_ENV
let probed = FORCE_ENV

function shouldFallback(err) {
  const status = err?.response?.status
  return status === 404 || status === 501 || status === 405
}

async function withFallback(projectId, realFn, mockFn) {
  if (useMock) return mockFn()
  try {
    const res = await realFn()
    probed = true
    return res
  } catch (err) {
    if (shouldFallback(err)) {
      useMock = true
      probed = true
      return mockFn()
    }
    throw err
  }
}

export function isPptMockMode() {
  return useMock
}

export function pptClientSyncContext(projectId, ctx) {
  mockPptApi.syncContext(projectId, ctx)
}

export const pptClient = {
  getStatus(projectId) {
    return withFallback(
      projectId,
      () => api.getDefensePpt(projectId),
      () => mockPptApi.getStatus(projectId),
    )
  },

  putCover(projectId, cover) {
    return withFallback(
      projectId,
      () => api.putDefensePptCover(projectId, cover),
      () => mockPptApi.putCover(projectId, cover),
    )
  },

  generate(projectId, body) {
    return withFallback(
      projectId,
      () => api.generateDefensePpt(projectId, body),
      () => mockPptApi.generate(projectId, body),
    )
  },

  getJob(projectId) {
    return withFallback(
      projectId,
      () => api.getDefensePptJob(projectId),
      () => mockPptApi.getJob(projectId),
    )
  },

  cancel(projectId) {
    return withFallback(
      projectId,
      () => api.cancelDefensePpt(projectId),
      () => mockPptApi.cancel(projectId),
    )
  },

  getDeck(projectId) {
    return withFallback(
      projectId,
      () => api.getDefensePptDeck(projectId),
      () => mockPptApi.getDeck(projectId),
    )
  },

  patchPage(projectId, pageId, patch) {
    return withFallback(
      projectId,
      () => api.patchDefensePptPage(projectId, pageId, patch),
      () => mockPptApi.patchPage(projectId, pageId, patch),
    )
  },

  patchSkin(projectId, body) {
    return withFallback(
      projectId,
      () => api.patchDefensePptSkin(projectId, body),
      () => mockPptApi.patchSkin(projectId, body),
    )
  },

  syncBiz(projectId) {
    return withFallback(
      projectId,
      () => api.syncDefensePptBiz(projectId),
      () => mockPptApi.syncBiz(projectId),
    )
  },

  check(projectId) {
    return withFallback(
      projectId,
      () => api.checkDefensePpt(projectId),
      () => mockPptApi.check(projectId),
    )
  },

  captureScreenshot(projectId, body) {
    return withFallback(
      projectId,
      () => api.captureDefensePptScreenshot(projectId, body),
      () => mockPptApi.captureScreenshot(projectId, body),
    )
  },

  uploadScreenshot(projectId, body) {
    return withFallback(
      projectId,
      () => api.uploadDefensePptScreenshot(projectId, body),
      () => mockPptApi.uploadScreenshot(projectId, body),
    )
  },

  /** 导出：mock 下本地 blob；真后端用 URL 打开 */
  async exportPptx(projectId) {
    if (useMock || FORCE_ENV) {
      const { blob, filename } = mockPptApi.exportBlob(projectId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 2000)
      return { mock: true, filename }
    }
    try {
      window.open(api.defensePptExportUrl(projectId), '_blank')
      return { mock: false }
    } catch (err) {
      if (shouldFallback(err)) {
        useMock = true
        return this.exportPptx(projectId)
      }
      throw err
    }
  },

  eventsUrl(projectId) {
    return api.defensePptEventsUrl(projectId)
  },

  /** 仅 mock：一键填演示封面 */
  fillDemoCover(projectId) {
    return mockPptApi.fillDemoCover(projectId)
  },

  markDirty(projectId) {
    return mockPptApi.markDirty(projectId)
  },

  get probed() {
    return probed
  },
}
