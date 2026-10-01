/**
 * 单据申请表单编排入口（list / browse）。
 * 两页 UI 分叉大：共享空表单默认值、成功文案与 schema 旗标；submit 仍留在各页。
 */
export { createEmptyTicketApplyForm, formatTicketApplySuccess } from './ticketApplyShared.js'
export { useTicketSchemaFlags } from './useTicketSchemaFlags.js'

import { reactive, ref } from 'vue'
import { createEmptyTicketApplyForm, formatTicketApplySuccess } from './ticketApplyShared.js'
import { useTicketSchemaFlags } from './useTicketSchemaFlags.js'
import { getSchema } from './domainSchema.js'

/**
 * @param {{ mode?: 'list' | 'browse' }} [opts]
 */
export function useTicketApplyForm(opts = {}) {
  const mode = opts.mode === 'browse' ? 'browse' : 'list'
  const flags = useTicketSchemaFlags()
  const form = reactive(createEmptyTicketApplyForm())
  const applyLoading = ref(false)
  const conflictTip = ref('')

  function resetForm() {
    Object.assign(form, createEmptyTicketApplyForm())
  }

  /** @param {object} data @param {{ checkinOnApply?: boolean }} [extra] */
  function successMessage(data, extra = {}) {
    return formatTicketApplySuccess(data, {
      autoApprove: !!flags.autoApprove.value,
      applyVerb: flags.applyVerb.value,
      getSchema,
      ...extra,
    })
  }

  return {
    mode,
    form,
    applyLoading,
    conflictTip,
    flags,
    resetForm,
    successMessage,
  }
}
