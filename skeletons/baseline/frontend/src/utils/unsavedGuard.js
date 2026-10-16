import { onBeforeUnmount, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox } from 'element-plus'

/**
 * 离开页或关闭窗口时，若 dirty 为真则提示。
 * @param {import('vue').Ref<boolean>|(() => boolean)} dirty
 */
export function useUnsavedGuard(dirty) {
  const isDirty = () => {
    const v = typeof dirty === 'function' ? dirty() : dirty?.value
    return !!v
  }

  function onBeforeUnload(e) {
    if (!isDirty()) return
    e.preventDefault()
    e.returnValue = ''
  }

  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

  onBeforeRouteLeave(async () => {
    if (!isDirty()) return true
    try {
      await ElMessageBox.confirm('还有未保存的内容，确定离开？', '离开确认', {
        type: 'warning',
        confirmButtonText: '离开',
        cancelButtonText: '继续编辑',
      })
      return true
    } catch {
      return false
    }
  })
}
