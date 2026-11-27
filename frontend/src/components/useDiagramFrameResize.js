import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { debounce } from '../opsShared'

/** 预览区最小高度（px） */
const FRAME_MIN = 160
/** 上方区域至少留一行可见（约 1.5em） */
const CHROME_MIN = 22
/** 拖条占位高度，与 CSS 对齐 */
const HANDLE_H = 10
/** 文案区与拖条之间留一点空隙（px） */
const CHROME_GAP = 6
/** 预留给 n-modal 标题栏 + 卡边距（约 7.5rem） */
const MODAL_CHROME_PX = 120

/**
 * 论文图模态 content-style：卡内不滚，由 viewer 自己分栏。
 * 与 .diagram-viewer-shell 高度配套，避免最小视口双滚动条。
 */
export const PAPER_DIAGRAM_CONTENT_STYLE = {
  maxHeight: 'calc(94vh - 3.5rem)',
  overflow: 'hidden',
  paddingBottom: '12px',
}

function viewerCapPx() {
  if (typeof window === 'undefined') return 760
  return Math.min(Math.max(280, window.innerHeight - MODAL_CHROME_PX), 760)
}

/**
 * 论文图预览区上下拖高：拖条在上方文案与预览框之间。
 * 打开时拖条贴在文案（含「复制描述」）下方一点；拖过之后不再被自动布局盖掉。
 */
export function useDiagramFrameResize() {
  const viewerRef = ref(null)
  const frameHeight = ref(FRAME_MIN)
  const resizing = ref(false)
  /** 用户拖过一次后锁定，避免 ResizeObserver 把手动高度打回 */
  const userResized = ref(false)
  let startY = 0
  let startH = 0
  let moveBound = null
  let upBound = null
  let resizeObs = null
  let layoutTimers = []

  function clampHeight(h) {
    const viewer = viewerRef.value
    const raw = Math.round(Number(h) || FRAME_MIN)
    const cap = viewer?.clientHeight > 0 ? viewer.clientHeight : viewerCapPx()
    const maxH = Math.max(FRAME_MIN, cap - CHROME_MIN - HANDLE_H)
    return Math.min(maxH, Math.max(FRAME_MIN, raw))
  }

  function preferredFrameHeight() {
    const viewer = viewerRef.value
    if (!viewer || viewer.clientHeight < 80) {
      // 模态尚未量到高度：先按视口估，随后 ResizeObserver / 延时再贴文案
      return clampHeight(viewerCapPx() - 280)
    }
    const chrome = viewer.querySelector('.diagram-chrome')
    const avail = Math.max(0, viewer.clientHeight - HANDLE_H)
    // chrome 改为按内容增高后，scrollHeight ≈ 文案真实高度（含描述块）
    const chromeWant = chrome
      ? Math.max(chrome.scrollHeight, chrome.offsetHeight, CHROME_MIN)
      : 280
    return clampHeight(avail - chromeWant - CHROME_GAP)
  }

  function applyPreferred() {
    if (userResized.value || resizing.value) return
    frameHeight.value = preferredFrameHeight()
  }

  // ResizeObserver 高频；debounce 后写 frameHeight，下游 fit 一并减负（P7）
  const applyPreferredDebounced = debounce(applyPreferred, 120)

  function detachWindowListeners() {
    if (moveBound) {
      window.removeEventListener('pointermove', moveBound)
      moveBound = null
    }
    if (upBound) {
      window.removeEventListener('pointerup', upBound)
      window.removeEventListener('pointercancel', upBound)
      upBound = null
    }
  }

  function onResizeDown(e) {
    if (e.button !== 0) return
    e.preventDefault()
    e.stopPropagation()
    resizing.value = true
    startY = e.clientY
    startH = frameHeight.value
    e.currentTarget?.setPointerCapture?.(e.pointerId)
    detachWindowListeners()
    moveBound = (ev) => {
      if (!resizing.value) return
      // 分栏：手柄下移 → 上方变高、预览变矮；上移 → 预览变高
      frameHeight.value = clampHeight(startH - (ev.clientY - startY))
    }
    upBound = () => {
      resizing.value = false
      userResized.value = true
      detachWindowListeners()
    }
    window.addEventListener('pointermove', moveBound)
    window.addEventListener('pointerup', upBound)
    window.addEventListener('pointercancel', upBound)
  }

  function onResizeMove(e) {
    if (!resizing.value) return
    frameHeight.value = clampHeight(startH - (e.clientY - startY))
  }

  function onResizeUp() {
    if (resizing.value) userResized.value = true
    resizing.value = false
    detachWindowListeners()
  }

  function clearLayoutTimers() {
    for (const t of layoutTimers) clearTimeout(t)
    layoutTimers = []
  }

  onMounted(async () => {
    await nextTick()
    applyPreferred()
    const viewer = viewerRef.value
    if (viewer && typeof ResizeObserver !== 'undefined') {
      resizeObs = new ResizeObserver(() => applyPreferredDebounced())
      resizeObs.observe(viewer)
      const chrome = viewer.querySelector('.diagram-chrome')
      if (chrome) resizeObs.observe(chrome)
    }
    // n-modal 开场动画 / 异步文案到位后再贴一次
    requestAnimationFrame(() => applyPreferred())
    for (const ms of [50, 200, 400]) {
      layoutTimers.push(setTimeout(applyPreferred, ms))
    }
  })

  onBeforeUnmount(() => {
    detachWindowListeners()
    clearLayoutTimers()
    applyPreferredDebounced.cancel?.()
    if (resizeObs) {
      resizeObs.disconnect()
      resizeObs = null
    }
  })

  const frameStyle = computed(() => ({
    height: `${frameHeight.value}px`,
    flex: '0 0 auto',
    maxHeight: 'none',
    minHeight: '0',
  }))

  return {
    viewerRef,
    frameHeight,
    frameStyle,
    resizing,
    onResizeDown,
    onResizeMove,
    onResizeUp,
    /** 文案/角色切换后重新贴拖条（未手拖时） */
    relayoutChrome: applyPreferred,
  }
}
