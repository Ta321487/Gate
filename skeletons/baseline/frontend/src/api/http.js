import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { isUnauthorizedPayload, kickToLogin } from '../utils/session.js'

const http = axios.create({ baseURL: '/', timeout: 15000, withCredentials: true })

http.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
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
    if (status === 401 || isUnauthorizedPayload(body)) {
      kickToLogin(router, body?.message || '登录已失效，请重新登录')
      return Promise.reject(err)
    }
    ElMessage.error(err.message || '网络错误')
    return Promise.reject(err)
  }
)

export default http
