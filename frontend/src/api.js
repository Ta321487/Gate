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
      timeout: 120000,
    })
  },
  getProject: (id, opts) => http.get(`/projects/${id}`, opts),
  getProjectPoll: (id) => http.get(`/projects/${id}`, POLL_OPTS),
  patchMatch: (id, body) => http.patch(`/projects/${id}/match`, body),
  generate: (id) => http.post(`/projects/${id}/generate`),
  deleteProject: (id, { keepDb = false } = {}) =>
    http.delete(`/projects/${id}`, { params: { keep_db: keepDb } }),
  downloadUrl: (id) => `/api/projects/${id}/download`,
  getSchema: (id) => http.get(`/projects/${id}/schema`),
  getApis: (id) => http.get(`/projects/${id}/apis`),
  erSvgUrl: (id) => `/api/projects/${id}/schema/er.svg`,
  runtime: (id) => http.get(`/projects/${id}/runtime`),
  runtimeAction: (id, side, action) => http.post(`/projects/${id}/runtime/${side}/${action}`),
  logs: (id, side, opts) => http.get(`/projects/${id}/logs/${side}`, opts),
  logsPoll: (id, side) => http.get(`/projects/${id}/logs/${side}`, POLL_OPTS),
  listJobs: (opts) => http.get('/jobs', opts),
  listJobsPoll: () => http.get('/jobs', POLL_OPTS),
  getJob: (id) => http.get(`/jobs/${id}`),
  cancelJob: (id) => http.post(`/jobs/${id}/cancel`),
  retryJob: (id) => http.post(`/jobs/${id}/retry`),
  purgeOrphanJobs: () => http.post('/jobs/purge-orphans'),
  deepseek: () => http.get('/deepseek'),
  saveDeepseek: (body) => http.put('/deepseek', body),
  testDeepseek: () => http.post('/deepseek/test'),
  deepseekBalance: () => http.get('/deepseek/balance'),
  deepseekUsage: (params) => http.get('/deepseek/usage', { params }),
  deepseekUsageChart: (params) => http.get('/deepseek/usage/chart', { params }),
  deepseekCalls: (params) => http.get('/deepseek/calls', { params }),
  system: () => http.get('/system'),
  freePorts: () => http.post('/system/free-ports'),
  catalog: () => http.get('/catalog'),
}

export default http
