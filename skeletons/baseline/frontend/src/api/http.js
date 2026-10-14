import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { schemaLabels } from '../utils/domainSchema.js'
import {
  isAccountDisabledPayload,
  isAccountLockedPayload,
  isUnauthorizedPayload,
  kickToLogin,
} from '../utils/session.js'

function lockedMessage(body) {
  const fromLabels = (schemaLabels()?.accountLockedHint || '').trim()
  return body?.message || fromLabels || '尝试次数过多，请稍后再登录'
}

const http = axios.create({ baseURL: '/', timeout: 15000, withCredentials: true })

http.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      if (isAccountLockedPayload(body)) {
        ElMessage.error(lockedMessage(body))
        return Promise.reject(body)
      }
      if (isAccountDisabledPayload(body)) {
        if (localStorage.getItem('token')) {
          kickToLogin(router, body.message || '账号已停用，请联系管理员')
        } else {
          ElMessage.error(body.message || '账号已停用，请联系管理员')
        }
        return Promise.reject(body)
      }
      if (isUnauthorizedPayload(body)) {
        kickToLogin(router, body.message || '登录已失效，请重新登录')
        return Promise.reject(body)
      }
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(body)
    }
    return body
  },
  (err) => {
    const status = err.response?.status
    const body = err.response?.data
    if (isAccountLockedPayload(body)) {
      ElMessage.error(lockedMessage(body))
      return Promise.reject(err)
    }
    if (isAccountDisabledPayload(body) || status === 401 || isUnauthorizedPayload(body)) {
      if (isAccountDisabledPayload(body) && !localStorage.getItem('token')) {
        ElMessage.error(body?.message || '账号已停用，请联系管理员')
        return Promise.reject(err)
      }
      kickToLogin(router, body?.message || '登录已失效，请重新登录')
      return Promise.reject(err)
    }
    ElMessage.error(err.message || '网络错误')
    return Promise.reject(err)
  }
)

export default http
