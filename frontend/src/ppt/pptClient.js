/**
 * 答辩 PPT API 客户端（真实后端）。
 */
import { api } from '../api.js'

export function pptClientSyncContext(_projectId, _ctx) {
  // no-op：就绪口径由后端 evidence / canDownload 判定
}

export const pptClient = {
  getStatus(projectId) {
    return api.getDefensePpt(projectId)
  },

  putCover(projectId, cover) {
    return api.putDefensePptCover(projectId, cover)
  },

  generate(projectId, body) {
    return api.generateDefensePpt(projectId, body)
  },

  getJob(projectId) {
    return api.getDefensePptJob(projectId)
  },

  cancel(projectId) {
    return api.cancelDefensePpt(projectId)
  },

  getDeck(projectId) {
    return api.getDefensePptDeck(projectId)
  },

  patchPage(projectId, pageId, patch) {
    return api.patchDefensePptPage(projectId, pageId, patch)
  },

  patchSkin(projectId, body) {
    return api.patchDefensePptSkin(projectId, body)
  },

  syncBiz(projectId) {
    return api.syncDefensePptBiz(projectId)
  },

  check(projectId) {
    return api.checkDefensePpt(projectId)
  },

  captureScreenshot(projectId, body) {
    return api.captureDefensePptScreenshot(projectId, body)
  },

  uploadScreenshot(projectId, body) {
    return api.uploadDefensePptScreenshot(projectId, body)
  },

  async exportPptx(projectId) {
    window.open(api.defensePptExportUrl(projectId), '_blank')
    return { mock: false }
  },

  eventsUrl(projectId) {
    return api.defensePptEventsUrl(projectId)
  },
}
