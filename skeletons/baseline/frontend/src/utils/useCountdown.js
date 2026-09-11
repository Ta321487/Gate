import { onMounted, onUnmounted, ref } from 'vue'
import { formatMmSs, parseDateMs } from './dates.js'

/**
 * 共用秒级时钟：支付超时、限时价、考试倒计时等复用，避免各页各写 setInterval。
 * @param {{ intervalMs?: number }} [opts]
 */
export function useNowTick(opts = {}) {
  const intervalMs = Number(opts.intervalMs) > 0 ? Number(opts.intervalMs) : 1000
  const nowMs = ref(Date.now())
  let timer = null

  onMounted(() => {
    nowMs.value = Date.now()
    timer = setInterval(() => {
      nowMs.value = Date.now()
    }, intervalMs)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
    timer = null
  })

  return { nowMs }
}

/** 距 deadline 剩余秒；已过返回 0；无效返回 null */
export function secondsUntil(deadlineRaw, nowMs = Date.now()) {
  const end = parseDateMs(deadlineRaw)
  if (end == null) return null
  return Math.max(0, Math.floor((end - nowMs) / 1000))
}

/** createdAt + minutes → 截止毫秒 */
export function deadlineFromCreated(createdAt, minutes) {
  const start = parseDateMs(createdAt)
  const mins = Number(minutes)
  if (start == null || !Number.isFinite(mins) || mins <= 0) return null
  return start + mins * 60 * 1000
}

export function formatCountdownClock(sec) {
  if (sec == null) return ''
  return formatMmSs(sec)
}

/** 是否进入紧急态（默认 ≤60s） */
export function isUrgentCountdown(sec, threshold = 60) {
  if (sec == null) return false
  return sec > 0 && sec <= threshold
}
