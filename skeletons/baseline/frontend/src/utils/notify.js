import { ElMessage } from 'element-plus'


export function notifyOk(msg = '已保存') {
  ElMessage.success(String(msg || '已保存'))
}

export function notifyFail(msg = '操作失败') {
  ElMessage.error(String(msg || '操作失败'))
}

export function notifyWarn(msg) {
  if (!msg) return
  ElMessage.warning(String(msg))
}
