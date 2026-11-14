import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

/** 预览区最小高度（px） */
const FRAME_MIN = 160
/** 上方区域至少留一行可见（约 1.5em） */
const CHROME_MIN = 22
/** 拖条占位高度，与 CSS 对齐 */
const HANDLE_H = 10
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
 * 打开时优先让上方（勾选/说明）整段可见；拖高时 chrome 可收缩，至少留一行。
 */
export function useDiagramFrameResize() {
  const viewerRef = ref(null)
  const frameHeight = ref(FRAME_MIN)
  const resizing = ref(false)
  let startY = 0
  let startH = 0
  let moveBound = null
  let upBound = null

  function clampHeight(h) {
    const viewer = viewerRef.value
    const raw = Math.round(Number(h) || FRAME_MIN)
    const cap = viewer?.clientHeight > 0 ? viewer.clientHeight : viewerCapPx()
    const maxH = Math.max(FRAME_MIN, cap - CHROME_MIN - HANDLE_H)
    return Math.min(maxH, Math.max(FRAME_MIN, raw))
  }

  function preferredFrameHeight() {
    const viewer = viewerRef.value
    if (!viewer) return clampHeight(viewerCapPx() - 280)
    const chrome = viewer.querySelector('.diagram-chrome')
    const avail = Math.max(0, viewer.clientHeight - HANDLE_H)
    const chromeWant = chrome ? chrome.scrollHeight : 280
    // 优先整段露出上方；塞不下时再让 chrome 内部滚动
    return clampHeight(avail - chromeWant)
  }

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
      frameHeight.value = clampHeight(startH + (ev.clientY - startY))
    }
    upBound = () => {
      resizing.value = false
      detachWindowListeners()
    }
    window.addEventListener('pointermove', moveBound)
    window.addEventListener('pointerup', upBound)
    window.addEventListener('pointercancel', upBound)
  }

  function onResizeMove(e) {
    if (!resizing.value) return
    frameHeight.value = clampHeight(startH + (e.clientY - startY))
  }

  function onResizeUp() {
    resizing.value = false
    detachWindowListeners()
  }

  onMounted(async () => {
    await nextTick()
    frameHeight.value = preferredFrameHeight()
  })

  onBeforeUnmount(() => {
    detachWindowListeners()
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
  }
}
