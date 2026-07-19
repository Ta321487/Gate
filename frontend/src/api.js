import axios from 'axios'
import { message } from './ui'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    return Promise.reject(err)
  }
)

export { message }
export { confirm, alert, prompt, dialog } from './ui'

export const api = {
  health: () => http.get('/health'),
  stats: () => http.get('/projects/stats'),
  listProjects: (params) => http.get('/projects', { params }),
  upload: (file, onProgress) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/projects/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
  },
  getProject: (id) => http.get(`/projects/${id}`),
  patchMatch: (id, body) => http.patch(`/projects/${id}/match`, body),
  generate: (id) => http.post(`/projects/${id}/generate`),
  deleteProject: (id, { keepDb = false } = {}) =>
    http.delete(`/projects/${id}`, { params: { keep_db: keepDb } }),
  downloadUrl: (id) => `/api/projects/${id}/download`,
  getSchema: (id) => http.get(`/projects/${id}/schema`),
  erSvgUrl: (id) => `/api/projects/${id}/schema/er.svg`,
  runtime: (id) => http.get(`/projects/${id}/runtime`),
  runtimeAction: (id, side, action) => http.post(`/projects/${id}/runtime/${side}/${action}`),
  logs: (id, side) => http.get(`/projects/${id}/logs/${side}`),
  listJobs: () => http.get('/jobs'),
  getJob: (id) => http.get(`/jobs/${id}`),
  cancelJob: (id) => http.post(`/jobs/${id}/cancel`),
  retryJob: (id) => http.post(`/jobs/${id}/retry`),
  purgeOrphanJobs: () => http.post('/jobs/purge-orphans'),
  deepseek: () => http.get('/deepseek'),
  saveDeepseek: (body) => http.put('/deepseek', body),
  testDeepseek: () => http.post('/deepseek/test'),
  deepseekBalance: () => http.get('/deepseek/balance'),
  deepseekUsage: (params) => http.get('/deepseek/usage', { params }),
  deepseekCalls: (params) => http.get('/deepseek/calls', { params }),
  system: () => http.get('/system'),
  freePorts: () => http.post('/system/free-ports'),
  catalog: () => http.get('/catalog'),
}

export default http
