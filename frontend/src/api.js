import axios from 'axios'
import { message } from './ui'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    // silent: 后台轮询等场景不弹全局错误（避免 reload 超时刷屏、卡死观感）
    if (!err.config?.silent) {
      const msg = err.response?.data?.detail || err.message || '请求失败'
      message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
    return Promise.reject(err)
  }
)

/** 生成中轮询：短超时 + 静默失败，后端 reload 时不挡下一轮 */
const POLL_OPTS = { silent: true, timeout: 8000 }

export { message }
export { confirm, alert, prompt, dialog } from './ui'

export const api = {
  health: () => http.get('/health'),
  stats: () => http.get('/projects/stats'),
  listProjects: (params) => http.get('/projects', { params }),
  upload: (files, onProgress) => {
    const list = Array.isArray(files) ? files : [files]
    const fd = new FormData()
    list.forEach((f) => {
      if (f) fd.append('files', f)
    })
    return http.post('/projects/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
      timeout: 300000,
    })
  },
  /** 多材料分堆预览（不建项目） */
  uploadPlan: (files, onProgress) => {
    const list = Array.isArray(files) ? files : [files]
    const fd = new FormData()
    list.forEach((f) => {
      if (f) fd.append('files', f)
    })
    return http.post('/projects/upload/plan', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
      timeout: 300000,
    })
  },
  /** 未确认分堆列表（刷新恢复） */
  uploadPlans: () => http.get('/projects/upload/plans'),
  /** 丢弃未确认分堆 */
  uploadPlanDelete: (planId) =>
    http.delete(`/projects/upload/plans/${encodeURIComponent(planId)}`),
  /** 确认分堆并创建项目 */
  uploadConfirm: (body) =>
    http.post('/projects/upload/confirm', body, { timeout: 600000 }),
  getProject: (id, opts) => http.get(`/projects/${id}`, opts),
  getProjectPoll: (id) => http.get(`/projects/${id}`, POLL_OPTS),
  patchMatch: (id, body) => http.patch(`/projects/${id}/match`, body),
  patchDelivery: (id, mark) => http.patch(`/projects/${id}/delivery`, { mark }),
  generate: (id) => http.post(`/projects/${id}/generate`),
  deleteProject: (id, { keepDb = false } = {}) =>
    http.delete(`/projects/${id}`, { params: { keep_db: keepDb } }),
  downloadUrl: (id) => `/api/projects/${id}/download`,
  getSchema: (id) => http.get(`/projects/${id}/schema`),
  getModules: (id, { layout = 'biz' } = {}) =>
    http.get(`/projects/${id}/schema/modules`, { params: { layout } }),
  getTestcases: (id, { fields = 6 } = {}) =>
    http.get(`/projects/${id}/schema/testcases`, { params: { fields } }),
  testcasesMdUrl: (id, { fields = 6 } = {}) => {
    const q = new URLSearchParams({ fields: String(fields) })
    return `/api/projects/${id}/schema/testcases.md?${q}`
  },
  getApis: (id) => http.get(`/projects/${id}/apis`),
  erSvgUrl: (id, { mode = 'total', entity } = {}) => {
    const q = new URLSearchParams({ mode })
    if (entity) q.set('entity', entity)
    return `/api/projects/${id}/schema/er.svg?${q}`
  },
  modulesSvgUrl: (id, { layout = 'biz' } = {}) => {
    const q = new URLSearchParams({ layout })
    return `/api/projects/${id}/schema/modules.svg?${q}`
  },
  runtime: (id) => http.get(`/projects/${id}/runtime`),
  runtimeAction: (id, side, action) => http.post(`/projects/${id}/runtime/${side}/${action}`),
  logs: (id, side, opts) => http.get(`/projects/${id}/logs/${side}`, opts),
  logsPoll: (id, side) => http.get(`/projects/${id}/logs/${side}`, POLL_OPTS),
  listJobs: (opts) => http.get('/jobs', opts),
  listJobsPoll: () => http.get('/jobs', POLL_OPTS),
  getJob: (id) => http.get(`/jobs/${id}`),
  cancelJob: (id) => http.post(`/jobs/${id}/cancel`),
  retryJob: (id) => http.post(`/jobs/${id}/retry`),
  deleteJob: (id) => http.delete(`/jobs/${id}`),
  purgeOrphanJobs: () => http.post('/jobs/purge-orphans'),
  purgeFinishedJobs: () => http.post('/jobs/purge-finished'),
  deepseek: () => http.get('/deepseek'),
  saveDeepseek: (body) => http.put('/deepseek', body),
  testDeepseek: () => http.post('/deepseek/test'),
  deepseekBalance: () => http.get('/deepseek/balance'),
  llmUsage: (params) => http.get('/llm/usage', { params }),
  llmUsageChart: (params) => http.get('/llm/usage/chart', { params }),
  llmUsageSupport: (params) => http.get('/llm/usage/support', { params }),
  llmProjectTokens: () => http.get('/llm/usage/project-tokens'),
  llmCalls: (params) => http.get('/llm/calls', { params }),
  gemini: () => http.get('/gemini'),
  saveGemini: (body) => http.put('/gemini', body),
  testGemini: () => http.post('/gemini/test'),
  unsplash: () => http.get('/unsplash'),
  testUnsplash: () => http.post('/unsplash/test'),
  system: () => http.get('/system'),
  freePorts: () => http.post('/system/free-ports'),
  catalog: () => http.get('/catalog'),
  sampleProposalPacks: () => http.get('/tools/sample-proposal/packs'),
  sampleProposal: (body) =>
    http.post('/tools/sample-proposal', body || {}, { timeout: 180000 }),
}

export default http
