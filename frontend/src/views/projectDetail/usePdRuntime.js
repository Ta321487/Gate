/**
 * 预览运行态（启停、地址、忙碌门闩）。挂入 useProjectDetail。
 */
import { computed, reactive, ref } from 'vue'
import { api, message } from '../../api'
import { runtimeCanStop } from './pdRuntimeFmt'

/**
 * @param {object} deps
 * @param {import('vue').Ref} deps.p
 * @param {import('vue').Ref<string>} deps.tab
 * @param {import('vue-router').RouteLocationNormalizedLoaded} deps.route
 * @param {{ load: Function, viewActive: Function, getViewEpoch: () => number }} deps.ctx
 */
export function usePdRuntime({ p, tab, route, ctx }) {
  const rt = reactive({
    backend_status: 'stopped',
    frontend_status: 'stopped',
    preview_url: null,
    backend_url: null,
    public_host: '127.0.0.1',
    backend_log_tail: '',
    frontend_log_tail: '',
  })
  const rtBusyBe = ref(false)
  const rtBusyFe = ref(false)
  const rtPendingAll = ref('')
  const rtAnyBusy = computed(() => rtBusyBe.value || rtBusyFe.value)
  const rtAllBusy = computed(() => rtBusyBe.value && rtBusyFe.value)
  /** IDE 式：已在跑就不能再启动；全停就不能关/重启；生成中禁止启动/重启 */
  const rtGenerating = computed(() => p.value?.status === 'generating')
  const rtBeLive = computed(() => runtimeCanStop(rt.backend_status))
  const rtFeLive = computed(() => runtimeCanStop(rt.frontend_status))
  const rtAnyLive = computed(() => rtBeLive.value || rtFeLive.value)
  const rtBothLive = computed(() => rtBeLive.value && rtFeLive.value)
  const rtCanStartAll = computed(
    () =>
      Boolean(p.value?.workspace_path) &&
      !rtGenerating.value &&
      !rtAnyBusy.value &&
      !rtBothLive.value,
  )
  const rtCanStopAll = computed(
    () => Boolean(p.value?.workspace_path) && !rtAnyBusy.value && rtAnyLive.value,
  )
  const rtCanRestartAll = computed(() => rtCanStopAll.value && !rtGenerating.value)
  const backendAddr = computed(() => {
    if (rt.backend_url) return rt.backend_url
    const host = rt.public_host || '127.0.0.1'
    const port = p.value?.backend_port
    return port ? `http://${host}:${port}` : ''
  })
  const frontendAddr = computed(() => {
    if (rt.preview_url) return rt.preview_url
    const host = rt.public_host || '127.0.0.1'
    const port = p.value?.frontend_port
    return port ? `http://${host}:${port}` : ''
  })
  const rtStartBlockedReason = computed(() => {
    const base = p.value?.preview_blocked_reason || ''
    if (base) return base
    if (!rtCanStartAll.value) {
      if (rtBothLive.value) return '前后端已在运行'
      if (rtAnyBusy.value) return '启停进行中 · 请稍候'
    }
    return ''
  })

  async function refreshRuntime(projectId) {
    const id = projectId || route.params.id
    if (!id || id === 'undefined' || id === 'null') return
    let data
    try {
      data = await api.runtime(id)
    } catch {
      return
    }
    if (route.params.id !== id) return
    rt.preview_url = data.preview_url || null
    rt.backend_url = data.backend_url || null
    rt.public_host = data.public_host || '127.0.0.1'
    if (p.value && p.value.id === id) {
      p.value.backend_port = data.backend_port || 0
      p.value.frontend_port = data.frontend_port || 0
      if (data.project_status) {
        p.value.status = data.project_status
        p.value.backend_running = ['starting', 'healthy'].includes(data.backend_status)
        p.value.frontend_running = ['starting', 'healthy'].includes(data.frontend_status)
      }
    }
    rt.backend_log_tail = data.backend_log_tail || ''
    rt.frontend_log_tail = data.frontend_log_tail || ''
    const be = data.backend_status || 'stopped'
    const fe = data.frontend_status || 'stopped'
    // 仅忙碌的那一侧保留中间态，另一侧照常刷新
    if (rtBusyBe.value) {
      if (rt.backend_status === 'stopping') {
        rt.backend_status = be === 'stopped' ? 'stopped' : 'stopping'
      } else if (rt.backend_status === 'starting') {
        rt.backend_status = be === 'stopped' ? 'starting' : be
      } else {
        rt.backend_status = be
      }
    } else {
      rt.backend_status = be
    }
    if (rtBusyFe.value) {
      if (rt.frontend_status === 'stopping') {
        rt.frontend_status = fe === 'stopped' ? 'stopped' : 'stopping'
      } else if (rt.frontend_status === 'starting') {
        rt.frontend_status = fe === 'stopped' ? 'starting' : fe
      } else {
        rt.frontend_status = fe
      }
    } else {
      rt.frontend_status = fe
    }
  }

  function _runtimeSettled(side, action) {
    const be = rt.backend_status
    const fe = rt.frontend_status
    const beDone = be !== 'starting' && be !== 'stopping'
    const feDone = fe !== 'starting' && fe !== 'stopping'
    if (side === 'backend') return beDone
    if (side === 'frontend') return feDone
    if (action === 'stop') return be === 'stopped' && fe === 'stopped'
    return beDone && feDone
  }

  async function rtAction(side, action) {
    const projectId = p.value?.id
    if (!projectId) return
    if (action === 'start' || action === 'restart') {
      const blocked = p.value?.preview_blocked_reason
      if (blocked) {
        message.warning(blocked)
        return
      }
    }
    const epoch = ctx.getViewEpoch()
    const touchBe = side === 'all' || side === 'backend'
    const touchFe = side === 'all' || side === 'frontend'
    if ((touchBe && rtBusyBe.value) || (touchFe && rtBusyFe.value)) return
    if (touchBe) rtBusyBe.value = true
    if (touchFe) rtBusyFe.value = true
    if (side === 'all') rtPendingAll.value = action

    if (action === 'start' || action === 'restart') {
      if (touchBe) rt.backend_status = 'starting'
      if (touchFe) rt.frontend_status = 'starting'
    } else if (action === 'stop') {
      if (touchBe) rt.backend_status = 'stopping'
      if (touchFe) rt.frontend_status = 'stopping'
    }
    try {
      await api.runtimeAction(projectId, side, action)
      if (!ctx.viewActive(projectId, epoch)) return
      await ctx.load({ id: projectId })
      if (!ctx.viewActive(projectId, epoch)) return
      const deadline = Date.now() + (action === 'stop' ? 8000 : 90000)
      while (Date.now() < deadline && ctx.viewActive(projectId, epoch) && tab.value === 'runtime') {
        await refreshRuntime(projectId)
        if (_runtimeSettled(side, action)) break
        await new Promise((r) => setTimeout(r, 700))
      }
    } finally {
      if (touchBe) rtBusyBe.value = false
      if (touchFe) rtBusyFe.value = false
      if (side === 'all') rtPendingAll.value = ''
      if (ctx.viewActive(projectId, epoch) && tab.value === 'runtime') {
        await refreshRuntime(projectId)
      }
    }
  }

  function openPreview() {
    if (rt.frontend_status !== 'healthy') {
      message.warning('前端未就绪，请先启动并等待可访问')
      return
    }
    const url = rt.preview_url || frontendAddr.value
    if (url) {
      window.open(url, '_blank')
      return
    }
    message.warning('前端未就绪，请先启动并等待可访问')
  }

  return {
    rt,
    rtBusyBe,
    rtBusyFe,
    rtPendingAll,
    rtAnyBusy,
    rtAllBusy,
    rtGenerating,
    rtBeLive,
    rtFeLive,
    rtAnyLive,
    rtBothLive,
    rtCanStartAll,
    rtCanStopAll,
    rtCanRestartAll,
    backendAddr,
    frontendAddr,
    rtStartBlockedReason,
    refreshRuntime,
    rtAction,
    openPreview,
    _runtimeSettled,
  }
}
