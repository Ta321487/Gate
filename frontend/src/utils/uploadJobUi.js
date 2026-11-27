/** 上传任务条相位 / 进度色（项目页 + 终稿吸收共用）。 */

export function formatUploadWaitSec(sec) {
  const s = Math.max(0, Number(sec) || 0)
  if (s < 60) return `${s} 秒`
  return `${Math.floor(s / 60)} 分 ${s % 60} 秒`
}

export function projectUploadJobPhaseLabel(job) {
  if (job.status === 'queued') return '待处理'
  if (job.status === 'uploading') return job.pct < 70 ? `上传中 ${job.pct}%` : '上传中'
  if (job.status === 'parsing') {
    return job.plan || job.name?.includes('确认') ? '正在创建项目' : '正在解析并分堆'
  }
  if (job.status === 'planned') {
    const n = job.plan?.clusters?.length
    const base = n != null ? `待确认分堆（${n} 个项目）` : '待确认分堆'
    return job.deferred ? `${base} · 已搁置` : base
  }
  if (job.status === 'done') {
    return job.projectId ? '项目已创建' : job.name?.includes('跳过') ? '已跳过' : '已完成'
  }
  if (job.status === 'error') return '上传失败'
  return ''
}

export function absorbUploadJobPhaseLabel(job) {
  if (job.status === 'uploading') {
    return job.pct > 0 ? `上传中 ${job.pct}%` : '上传中'
  }
  if (job.status === 'extracting') {
    return `抽取中 · ${formatUploadWaitSec(job.elapsedSec)}`
  }
  if (job.status === 'done') return '已抽取'
  if (job.status === 'error') return '抽取失败'
  return ''
}

export function uploadJobBarColor(job) {
  if (job.status === 'error') return 'var(--danger, #c45c5c)'
  if (job.status === 'done') return 'var(--green)'
  if (job.status === 'planned') return 'var(--teal, #2a9d8f)'
  if (job.status === 'queued') return 'var(--line-soft)'
  return ''
}
