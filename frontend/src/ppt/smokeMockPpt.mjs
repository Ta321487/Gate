/**
 * mock 答辩 PPT 状态机冒烟（node）
 * 运行：node frontend/src/ppt/smokeMockPpt.mjs
 */
import { mockPptApi, resetMockPptStore } from './mockPptApi.js'
import { coverFieldsComplete } from './types.js'

function assert(cond, msg) {
  if (!cond) throw new Error(msg)
}

async function waitUntil(fn, ms = 8000) {
  const start = Date.now()
  while (Date.now() - start < ms) {
    if (await fn()) return
    await new Promise((r) => setTimeout(r, 200))
  }
  throw new Error('timeout')
}

async function main() {
  resetMockPptStore()
  const id = 'smoke-proj'

  // locked
  mockPptApi.syncContext(id, { title: '冒烟题', canDownload: false })
  let st = await mockPptApi.getStatus(id)
  assert(st.phase === 'locked', `expected locked, got ${st.phase}`)

  // ready
  mockPptApi.syncContext(id, { canDownload: true })
  st = await mockPptApi.getStatus(id)
  assert(st.phase === 'ready', `expected ready, got ${st.phase}`)

  // cover gate
  let rejected = false
  try {
    await mockPptApi.generate(id, {})
  } catch {
    rejected = true
  }
  assert(rejected, 'generate without cover should fail')

  await mockPptApi.fillDemoCover(id)
  st = await mockPptApi.getStatus(id)
  assert(coverFieldsComplete(st.cover), 'demo cover incomplete')

  // generating → done
  await mockPptApi.generate(id, {
    cover: st.cover,
    theme: 'scholar',
    layout_family: 'band',
    master: 'none',
  })
  st = await mockPptApi.getStatus(id)
  assert(st.phase === 'generating', `expected generating, got ${st.phase}`)

  await waitUntil(async () => {
    const s = await mockPptApi.getStatus(id)
    return s.phase === 'done'
  })
  st = await mockPptApi.getStatus(id)
  assert(st.has_deck, 'deck missing after generate')
  const deck = await mockPptApi.getDeck(id)
  assert(deck.pages?.length >= 8, 'too few pages')

  // check: demo shot missing → cannot export
  let check = await mockPptApi.check(id)
  assert(!check.can_export, 'should block export without demo shot')
  assert(check.items.some((i) => i.code === 'demo_shot'), 'missing demo_shot error')

  await mockPptApi.captureScreenshot(id, { pageId: 'demo' })
  check = await mockPptApi.check(id)
  assert(check.can_export, 'should allow export after shot')

  // dirty → block export
  mockPptApi.markDirty(id)
  st = await mockPptApi.getStatus(id)
  assert(st.phase === 'dirty', `expected dirty, got ${st.phase}`)
  check = await mockPptApi.check(id)
  assert(!check.can_export, 'dirty should block export')

  // sync biz respects locked
  const page = deck.pages.find((p) => p.id === 'background')
  const lockedBefore = page.bullets.find((b) => b.locked)
  const sync = await mockPptApi.syncBiz(id)
  assert(sync.kept >= 1, 'should keep locked')
  assert(sync.updated >= 1, 'should update unlocked')
  st = await mockPptApi.getStatus(id)
  assert(st.phase === 'done', 'after sync should be done')
  const deck2 = await mockPptApi.getDeck(id)
  const lockedAfter = deck2.pages.find((p) => p.id === 'background').bullets.find((b) => b.id === lockedBefore.id)
  assert(lockedAfter.text === lockedBefore.text, 'locked text changed')

  console.log('smokeMockPpt: OK')
  resetMockPptStore()
}

main().catch((e) => {
  console.error('smokeMockPpt FAIL', e)
  process.exit(1)
})
