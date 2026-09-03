/**
 * 答辩 PPT 状态机与操作（挂入 useProjectDetail）。
 */
import { computed, reactive, ref, watch } from 'vue'
import { message } from '../api.js'
import { coverFieldsComplete, EMPTY_COVER, PPT_DIRTY_BANNER } from './types.js'
import {
  PPT_THEME_OPTIONS,
  PPT_LAYOUT_OPTIONS,
  PPT_MASTER_OPTIONS,
  seedThemeForProject,
} from './deckDefaults.js'
import { pptClient, pptClientSyncContext } from './pptClient.js'

/**
 * @param {object} deps
 * @param {import('vue').Ref} deps.p
 * @param {import('vue').ComputedRef<boolean>} deps.canDownload
 * @param {import('vue').Ref<string>} deps.tab
 * @param {import('vue').Ref<string>} deps.artifactView
 * @param {(view?: string) => void} deps.goArtifacts
 */
export function useDefensePpt({ p, canDownload, tab, artifactView, goArtifacts }) {
  const pptStatus = ref(null)
  const pptDeck = ref(null)
  const pptJob = ref(null)
  const pptLoading = ref(false)
  const pptActing = ref('')
  const pptPageIndex = ref(0)
  const pptCheckResult = ref(null)
  const showPptCheck = ref(false)
  const pptCover = reactive({ ...EMPTY_COVER() })
  const pptSkin = reactive({
    theme: 'scholar',
    layout_family: 'band',
    master: 'none',
  })

  let pptPollTimer = null
  let pptEs = null

  const pptPhase = computed(() => {
    const st = pptStatus.value
    if (!st) return canDownload.value ? 'ready' : 'locked'
    // 前端以 canDownload 覆盖 locked/ready 门闩（与 ZIP 同口径）
    if (st.phase === 'generating') return 'generating'
    if (st.has_deck || st.phase === 'done' || st.phase === 'dirty') {
      return st.biz_dirty || st.phase === 'dirty' ? 'dirty' : 'done'
    }
    if (!canDownload.value) return 'locked'
    return 'ready'
  })

  const pptEvidence = computed(() => {
    const e = pptStatus.value?.evidence
    if (e) {
      return {
        ...e,
        gates_overall: canDownload.value,
      }
    }
    const ok = canDownload.value
    return {
      proposal: ok,
      modules: ok,
      er: ok,
      testcases: ok,
      gates_overall: ok,
    }
  })

  const pptCoverComplete = computed(() => coverFieldsComplete(pptCover))
  const pptHasDeck = computed(
    () => pptPhase.value === 'done' || pptPhase.value === 'dirty' || !!pptDeck.value,
  )
  const pptBizDirty = computed(
    () => pptPhase.value === 'dirty' || !!pptStatus.value?.biz_dirty,
  )
  const pptCanGenerate = computed(
    () =>
      (pptPhase.value === 'ready' || pptPhase.value === 'done' || pptPhase.value === 'dirty') &&
      pptCoverComplete.value &&
      !pptActing.value &&
      canDownload.value &&
      pptPhase.value !== 'generating',
  )
  const pptCanExport = computed(() => {
    if (!pptHasDeck.value || pptBizDirty.value || !canDownload.value) return false
    const check = pptCheckResult.value
    if (check && check.can_export === false) return false
    if (check?.items?.some((i) => i.level === 'error')) return false
    return true
  })
  const pptDeckSummary = computed(() => {
    if (pptStatus.value?.deck_summary) return pptStatus.value.deck_summary
    if (!pptDeck.value) return ''
    return `${pptDeck.value.pages?.length || 0}页 · ${pptDeck.value.theme} · ${pptDeck.value.layout_family}`
  })
  const pptFingerprintHint = computed(() =>
    pptBizDirty.value ? '业务指纹脏 · 禁止导出' : '与工程一致',
  )
  const pptDirtyBanner = PPT_DIRTY_BANNER
  const pptThemeOptions = PPT_THEME_OPTIONS
  const pptLayoutOptions = PPT_LAYOUT_OPTIONS
  const pptMasterOptions = PPT_MASTER_OPTIONS
  const pptCurrentPage = computed(() => pptDeck.value?.pages?.[pptPageIndex.value] || null)

  function syncCoverFromStatus(st) {
    if (!st?.cover) return
    Object.assign(pptCover, { ...EMPTY_COVER(), ...st.cover })
    pptSkin.theme = st.theme || pptSkin.theme
    pptSkin.layout_family = st.layout_family || pptSkin.layout_family
    pptSkin.master = st.master || pptSkin.master
  }

  function stopPptPoll() {
    if (pptPollTimer) {
      clearInterval(pptPollTimer)
      pptPollTimer = null
    }
    if (pptEs) {
      try {
        pptEs.close()
      } catch {
        /* ignore */
      }
      pptEs = null
    }
  }

  async function refreshPptStatus({ loadDeck = false } = {}) {
    if (!p.value?.id) {
      pptStatus.value = null
      pptDeck.value = null
      pptJob.value = null
      return
    }
    pptClientSyncContext(p.value.id, {
      title: p.value.title,
      canDownload: canDownload.value,
    })
    try {
      const st = await pptClient.getStatus(p.value.id)
      pptStatus.value = st
      syncCoverFromStatus(st)
      if (st.job) pptJob.value = st.job
      if (st.phase === 'generating' || st.job?.status === 'running') {
        startPptPoll()
      } else {
        stopPptPoll()
      }
      if (loadDeck || st.has_deck) {
        try {
          pptDeck.value = await pptClient.getDeck(p.value.id)
          if (pptPageIndex.value >= (pptDeck.value.pages?.length || 0)) {
            pptPageIndex.value = 0
          }
        } catch {
          /* 尚无 deck */
        }
      }
    } catch (err) {
      console.warn('[defense-ppt] status', err)
    }
  }

  async function pollPptJob() {
    if (!p.value?.id) return
    try {
      const job = await pptClient.getJob(p.value.id)
      if (job) pptJob.value = job
      const st = await pptClient.getStatus(p.value.id)
      pptStatus.value = st
      if (job?.status === 'succeeded' || st.phase === 'done' || st.phase === 'dirty') {
        stopPptPoll()
        pptDeck.value = await pptClient.getDeck(p.value.id)
        message.success('答辩 PPT 已生成')
      } else if (job?.status === 'failed' || job?.status === 'cancelled') {
        stopPptPoll()
        if (job.status === 'failed') message.error(job.error || '答辩 PPT 生成失败')
      }
    } catch (err) {
      console.warn('[defense-ppt] poll', err)
    }
  }

  function startPptPoll() {
    if (pptPollTimer) return
    pptPollTimer = setInterval(pollPptJob, 800)
    // 尝试 SSE（后端有则用；失败忽略，靠 poll）
    if (!pptEs && p.value?.id) {
      try {
        const es = new EventSource(pptClient.eventsUrl(p.value.id))
        pptEs = es
        es.onmessage = () => {
          pollPptJob()
        }
        es.onerror = () => {
          try {
            es.close()
          } catch {
            /* ignore */
          }
          if (pptEs === es) pptEs = null
        }
      } catch {
        /* ignore */
      }
    }
  }

  async function savePptCover() {
    if (!p.value?.id) return
    pptActing.value = 'cover'
    try {
      const st = await pptClient.putCover(p.value.id, { ...pptCover })
      pptStatus.value = st
      message.success('封面信息已保存')
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '保存失败'
      message.error(typeof msg === 'string' ? msg : '保存失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function startPptGenerate() {
    if (!p.value?.id || !pptCanGenerate.value) return
    pptActing.value = 'generate'
    try {
      await pptClient.putCover(p.value.id, { ...pptCover })
      const res = await pptClient.generate(p.value.id, {
        cover: { ...pptCover },
        theme: pptSkin.theme,
        layout_family: pptSkin.layout_family,
        master: pptSkin.master,
      })
      pptStatus.value = res
      if (res.job) pptJob.value = res.job
      else if (res.job_id) pptJob.value = { id: res.job_id, progress: 0, status: 'running' }
      startPptPoll()
      message.success('已开始生成答辩 PPT')
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '开跑失败'
      message.error(typeof msg === 'string' ? msg : '开跑失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function cancelPptGenerate() {
    if (!p.value?.id) return
    pptActing.value = 'cancel'
    try {
      const st = await pptClient.cancel(p.value.id)
      pptStatus.value = st
      stopPptPoll()
      message.info('已取消答辩 PPT 生成')
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '取消失败'
      message.error(typeof msg === 'string' ? msg : '取消失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function loadPptDeck() {
    if (!p.value?.id) return
    pptLoading.value = true
    try {
      pptDeck.value = await pptClient.getDeck(p.value.id)
      await refreshPptStatus()
    } catch {
      pptDeck.value = null
    } finally {
      pptLoading.value = false
    }
  }

  async function patchPptPage(pageId, patch) {
    if (!p.value?.id) return
    pptActing.value = 'patch'
    try {
      const page = await pptClient.patchPage(p.value.id, pageId, patch)
      if (pptDeck.value) {
        const idx = pptDeck.value.pages.findIndex((x) => x.id === pageId)
        if (idx >= 0) pptDeck.value.pages[idx] = page
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '保存失败'
      message.error(typeof msg === 'string' ? msg : '保存失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function savePptBullet(pageId, bulletId, text, locked) {
    const page = pptDeck.value?.pages?.find((x) => x.id === pageId)
    if (!page?.bullets) return
    const bullets = page.bullets.map((b) =>
      b.id === bulletId ? { ...b, text, locked: locked ?? b.locked } : { ...b },
    )
    await patchPptPage(pageId, { bullets })
  }

  async function togglePptBulletLock(pageId, bulletId) {
    const page = pptDeck.value?.pages?.find((x) => x.id === pageId)
    const b = page?.bullets?.find((x) => x.id === bulletId)
    if (!b) return
    await savePptBullet(pageId, bulletId, b.text, !b.locked)
  }

  async function applyPptSkin() {
    if (!p.value?.id) return
    pptActing.value = 'skin'
    try {
      const st = await pptClient.patchSkin(p.value.id, { ...pptSkin })
      pptStatus.value = st
      if (pptDeck.value) {
        pptDeck.value.theme = pptSkin.theme
        pptDeck.value.layout_family = pptSkin.layout_family
        pptDeck.value.master = pptSkin.master
      }
      message.success('主题/版式已切换 · 换皮不标脏')
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '换皮失败'
      message.error(typeof msg === 'string' ? msg : '换皮失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function syncPptBiz() {
    if (!p.value?.id) return
    pptActing.value = 'sync'
    try {
      const res = await pptClient.syncBiz(p.value.id)
      pptStatus.value = res
      pptDeck.value = await pptClient.getDeck(p.value.id)
      message.success(res.message || `已更新 ${res.updated} 处；保留人工修改 ${res.kept} 处`)
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '更新失败'
      message.error(typeof msg === 'string' ? msg : '更新失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function runPptCheck() {
    if (!p.value?.id) return
    pptActing.value = 'check'
    try {
      pptCheckResult.value = await pptClient.check(p.value.id)
      showPptCheck.value = true
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '检查失败'
      message.error(typeof msg === 'string' ? msg : '检查失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function exportPptx() {
    if (!p.value?.id) return
    if (pptBizDirty.value) {
      message.warning('业务内容可能不一致，请先按工程更新业务页')
      return
    }
    if (!canDownload.value) {
      message.warning('bake 门禁未通过，禁止导出')
      return
    }
    pptActing.value = 'export'
    try {
      // 导出前再检查一次
      const check = await pptClient.check(p.value.id)
      pptCheckResult.value = check
      if (!check.can_export) {
        showPptCheck.value = true
        message.warning('检查未通过，暂不可导出')
        return
      }
      await pptClient.exportPptx(p.value.id)
      message.success('已开始下载 PPTX（不进学生 ZIP）')
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '导出失败'
      message.error(typeof msg === 'string' ? msg : '导出失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function capturePptScreenshot(pageId) {
    if (!p.value?.id) return
    pptActing.value = 'shot'
    try {
      await pptClient.captureScreenshot(p.value.id, { pageId })
      pptDeck.value = await pptClient.getDeck(p.value.id)
      message.success(res?.ok ? '已采集截图' : (res?.figure?.hint || '采图未成功，请上传'))
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '采集失败'
      message.error(typeof msg === 'string' ? msg : '采集失败')
    } finally {
      pptActing.value = ''
    }
  }

  async function uploadPptScreenshot(pageId, dataUrl) {
    if (!p.value?.id) return
    pptActing.value = 'shot'
    try {
      await pptClient.uploadScreenshot(p.value.id, { pageId, dataUrl })
      pptDeck.value = await pptClient.getDeck(p.value.id)
      message.success('已替换截图')
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '上传失败'
      message.error(typeof msg === 'string' ? msg : '上传失败')
    } finally {
      pptActing.value = ''
    }
  }

  function openPptCompare() {
    goArtifacts('ppt')
  }

  function initPptSkinSeed() {
    if (!p.value?.id) return
    const seed = seedThemeForProject(p.value.id)
    if (!pptStatus.value?.has_deck) {
      pptSkin.theme = seed.theme
      pptSkin.layout_family = seed.layout_family
    }
  }

  function disposePpt() {
    stopPptPoll()
    pptStatus.value = null
    pptDeck.value = null
    pptJob.value = null
    pptCheckResult.value = null
    showPptCheck.value = false
    Object.assign(pptCover, EMPTY_COVER())
  }

  watch(canDownload, (ok) => {
    if (p.value?.id) {
      pptClientSyncContext(p.value.id, { title: p.value.title, canDownload: ok })
      refreshPptStatus()
    }
  })

  return {
    pptStatus,
    pptDeck,
    pptJob,
    pptLoading,
    pptActing,
    pptPageIndex,
    pptCheckResult,
    showPptCheck,
    pptCover,
    pptSkin,
    pptPhase,
    pptEvidence,
    pptCoverComplete,
    pptHasDeck,
    pptBizDirty,
    pptCanGenerate,
    pptCanExport,
    pptDeckSummary,
    pptFingerprintHint,
    pptDirtyBanner,
    pptThemeOptions,
    pptLayoutOptions,
    pptMasterOptions,
    pptCurrentPage,
    refreshPptStatus,
    stopPptPoll,
    disposePpt,
    savePptCover,
    startPptGenerate,
    cancelPptGenerate,
    loadPptDeck,
    patchPptPage,
    savePptBullet,
    togglePptBulletLock,
    applyPptSkin,
    syncPptBiz,
    runPptCheck,
    exportPptx,
    capturePptScreenshot,
    uploadPptScreenshot,
    openPptCompare,
    initPptSkinSeed,
  }
}
