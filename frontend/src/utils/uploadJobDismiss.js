/**
 * 上传任务条：成功短留后自动消失；失败留着等人处理。
 * 对标成熟 B 端：done → toast + 延迟收起；error / 待确认 → 不自动清。
 */
export const UPLOAD_JOB_AUTO_DISMISS_MS = 2500

export function cancelUploadJobAutoDismiss(job) {
  if (!job?._autoDismissTimer) return
  clearTimeout(job._autoDismissTimer)
  job._autoDismissTimer = null
}

/** @param {{ id: string|number }} job @param {(id: string|number) => void} dismissFn */
export function scheduleUploadJobAutoDismiss(
  job,
  dismissFn,
  ms = UPLOAD_JOB_AUTO_DISMISS_MS,
) {
  if (!job?.id || typeof dismissFn !== 'function') return
  cancelUploadJobAutoDismiss(job)
  job._autoDismissTimer = setTimeout(() => {
    job._autoDismissTimer = null
    dismissFn(job.id)
  }, ms)
}
