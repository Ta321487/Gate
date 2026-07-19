import { h } from 'vue'
import { createDiscreteApi, NInput, zhCN, dateZhCN } from 'naive-ui'

const { message, dialog } = createDiscreteApi(['message', 'dialog'], {
  configProviderProps: { locale: zhCN, dateLocale: dateZhCN },
})

/** @returns {Promise<boolean>} */
export function confirm(content, options = {}) {
  const {
    title = '确认',
    positiveText = '确定',
    negativeText = '取消',
    type = 'warning',
  } = options
  return new Promise((resolve) => {
    const api = type === 'error' ? dialog.error
      : type === 'info' ? dialog.info
        : type === 'success' ? dialog.success
          : dialog.warning
    let settled = false
    const finish = (ok) => {
      if (settled) return
      settled = true
      resolve(ok)
    }
    api({
      title,
      content,
      positiveText,
      negativeText,
      closable: true,
      maskClosable: false,
      onPositiveClick: () => finish(true),
      onNegativeClick: () => finish(false),
      onClose: () => finish(false),
    })
  })
}

/** @returns {Promise<void>} */
export function alert(content, options = {}) {
  const {
    title = '提示',
    positiveText = '知道了',
    type = 'info',
  } = options
  return new Promise((resolve) => {
    const api = type === 'error' ? dialog.error
      : type === 'warning' ? dialog.warning
        : type === 'success' ? dialog.success
          : dialog.info
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      resolve()
    }
    api({
      title,
      content,
      positiveText,
      closable: true,
      maskClosable: false,
      onPositiveClick: () => finish(),
      onClose: () => finish(),
    })
  })
}

/**
 * @returns {Promise<string|null>} 取消为 null
 */
export function prompt(content, options = {}) {
  const {
    title = '请输入',
    positiveText = '确定',
    negativeText = '取消',
    defaultValue = '',
    placeholder = '',
    type = 'info',
  } = options
  let current = defaultValue
  return new Promise((resolve) => {
    const api = type === 'warning' ? dialog.warning
      : type === 'error' ? dialog.error
        : dialog.info
    let settled = false
    const finish = (v) => {
      if (settled) return
      settled = true
      resolve(v)
    }
    api({
      title,
      content: () => h('div', { style: 'margin-top:8px' }, [
        content ? h('p', { style: 'margin:0 0 12px' }, content) : null,
        h(NInput, {
          defaultValue,
          placeholder,
          autofocus: true,
          onUpdateValue: (v) => { current = v },
          onKeyup: (e) => {
            if (e.key === 'Enter') finish(String(current ?? ''))
          },
        }),
      ]),
      positiveText,
      negativeText,
      closable: true,
      maskClosable: false,
      onPositiveClick: () => finish(String(current ?? '')),
      onNegativeClick: () => finish(null),
      onClose: () => finish(null),
    })
  })
}

export { message, dialog }
