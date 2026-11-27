import { nextTick, watch } from 'vue'
import { debounce } from '../opsShared'

/**
 * 论文图预览：frameHeight 变化时 debounce 再 fitToFrame（P7）。
 * 各 DiagramViewer 共用，禁止每文件复制一套。
 */
export function watchFrameHeightFit(frameHeight, fitToFrame, ms = 120) {
  const run = debounce(async () => {
    await nextTick()
    if (typeof fitToFrame === 'function') fitToFrame()
  }, ms)
  return watch(frameHeight, () => {
    run()
  })
}
