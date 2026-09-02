import { EMPTY_COVER, coverFieldsComplete, emptyEvidence } from './types.js'
import {
  PPT_PIPELINE_STEPS,
  PPT_UNIT_DEFS,
  buildSampleDeck,
  seedThemeForProject,
  DEMO_BADGE,
} from './deckDefaults.js'

/** @type {Map<string, object>} */
const store = new Map()

function key(projectId) {
  return String(projectId)
}

function ensure(projectId, opts = {}) {
  const k = key(projectId)
  if (!store.has(k)) {
    const seed = seedThemeForProject(projectId)
    store.set(k, {
      cover: EMPTY_COVER(),
      theme: seed.theme,
      layout_family: seed.layout_family,
      master: seed.master,
      deck: null,
      biz_dirty: false,
      job: null,
      genTimer: null,
      title: opts.title || '毕业设计答辩',
      canDownload: !!opts.canDownload,
      missingDemoShot: true,
    })
  }
  const s = store.get(k)
  if (opts.title) s.title = opts.title
  if ('canDownload' in opts) s.canDownload = !!opts.canDownload
  return s
}

function evidenceOf(s) {
  const ok = !!s.canDownload
  return {
    proposal: ok,
    modules: ok,
    er: ok,
    testcases: ok,
    gates_overall: ok,
  }
}

function derivePhase(s) {
  if (s.job && (s.job.status === 'running' || s.job.status === 'queued')) return 'generating'
  if (!s.canDownload) return 'locked'
  if (s.deck) return s.biz_dirty ? 'dirty' : 'done'
  return 'ready'
}

function statusPayload(projectId) {
  const s = ensure(projectId)
  const phase = derivePhase(s)
  return {
    phase,
    evidence: evidenceOf(s),
    cover: { ...s.cover },
    theme: s.theme,
    layout_family: s.layout_family,
    master: s.master,
    biz_dirty: !!s.biz_dirty,
    has_deck: !!s.deck,
    page_count: s.deck?.pages?.length || 0,
    job: s.job ? { ...s.job } : null,
    title: s.title,
    deck_summary: s.deck
      ? `${s.deck.pages.length}页 · ${s.theme} · ${s.layout_family}`
      : '',
  }
}

function advanceJob(projectId) {
  const s = ensure(projectId)
  if (!s.job || s.job.status !== 'running') return
  const progress = Math.min(100, (s.job.progress || 0) + 18)
  const steps = (s.job.steps || []).map((st) => ({ ...st }))
  const units = (s.job.units || []).map((u) => ({ ...u }))

  const stepIdx = Math.min(steps.length - 1, Math.floor(progress / 22))
  steps.forEach((st, i) => {
    if (i < stepIdx) st.status = 'done'
    else if (i === stepIdx) st.status = 'running'
    else st.status = 'pending'
  })
  const unitIdx = Math.min(units.length - 1, Math.floor((progress / 100) * units.length))
  units.forEach((u, i) => {
    if (i < unitIdx) u.status = 'done'
    else if (i === unitIdx) u.status = 'generating'
    else u.status = 'queued'
  })

  s.job = { ...s.job, progress, steps, units }

  if (progress >= 100) {
    steps.forEach((st) => {
      st.status = 'done'
    })
    units.forEach((u) => {
      u.status = 'done'
    })
    s.job = { ...s.job, progress: 100, status: 'succeeded', steps, units }
    s.deck = buildSampleDeck({
      title: s.title,
      cover: s.cover,
      theme: s.theme,
      layout_family: s.layout_family,
      master: s.master,
    })
    s.biz_dirty = false
    if (s.genTimer) {
      clearInterval(s.genTimer)
      s.genTimer = null
    }
  }
}

export const mockPptApi = {
  /** 供 UI 在无后端时同步 canDownload */
  syncContext(projectId, { title, canDownload } = {}) {
    ensure(projectId, { title, canDownload })
  },

  /** 演示：强制标脏 */
  markDirty(projectId) {
    const s = ensure(projectId)
    if (s.deck) s.biz_dirty = true
    return statusPayload(projectId)
  },

  getStatus(projectId) {
    return Promise.resolve(statusPayload(projectId))
  },

  putCover(projectId, cover) {
    const s = ensure(projectId)
    s.cover = { ...EMPTY_COVER(), ...cover }
    if (s.deck) {
      s.deck.cover = { ...s.cover }
      const page = s.deck.pages.find((p) => p.role === 'cover')
      if (page) page.cover = { ...s.cover }
    }
    return Promise.resolve(statusPayload(projectId))
  },

  generate(projectId, body = {}) {
    const s = ensure(projectId)
    if (!s.canDownload) {
      return Promise.reject({ response: { status: 409, data: { detail: '程序未就绪（bake 门禁未过）' } } })
    }
    if (!coverFieldsComplete(body.cover || s.cover)) {
      return Promise.reject({ response: { status: 400, data: { detail: '封面信息未齐（含校徽）' } } })
    }
    if (body.cover) s.cover = { ...EMPTY_COVER(), ...body.cover }
    if (body.theme) s.theme = body.theme
    if (body.layout_family) s.layout_family = body.layout_family
    if (body.master) s.master = body.master

    if (s.genTimer) clearInterval(s.genTimer)
    s.job = {
      id: 80 + Math.floor(Math.random() * 20),
      progress: 8,
      status: 'running',
      steps: PPT_PIPELINE_STEPS.map((st, i) => ({
        ...st,
        status: i === 0 ? 'running' : 'pending',
        meta: '',
      })),
      units: PPT_UNIT_DEFS.map((u, i) => ({
        ...u,
        status: i === 0 ? 'generating' : 'queued',
        meta: '',
      })),
    }
    s.genTimer = setInterval(() => advanceJob(projectId), 700)
    return Promise.resolve({ job_id: s.job.id, ...statusPayload(projectId) })
  },

  getJob(projectId) {
    const s = ensure(projectId)
    return Promise.resolve(s.job ? { ...s.job } : null)
  },

  cancel(projectId) {
    const s = ensure(projectId)
    if (s.genTimer) {
      clearInterval(s.genTimer)
      s.genTimer = null
    }
    if (s.job) s.job = { ...s.job, status: 'cancelled' }
    return Promise.resolve(statusPayload(projectId))
  },

  getDeck(projectId) {
    const s = ensure(projectId)
    if (!s.deck) {
      return Promise.reject({ response: { status: 404, data: { detail: '尚无答辩 PPT' } } })
    }
    return Promise.resolve(JSON.parse(JSON.stringify(s.deck)))
  },

  patchPage(projectId, pageId, patch) {
    const s = ensure(projectId)
    if (!s.deck) {
      return Promise.reject({ response: { status: 404, data: { detail: '尚无答辩 PPT' } } })
    }
    const page = s.deck.pages.find((p) => p.id === pageId)
    if (!page) {
      return Promise.reject({ response: { status: 404, data: { detail: '页不存在' } } })
    }
    if (patch.bullets) page.bullets = patch.bullets
    if (patch.title) page.title = patch.title
    if (patch.cover) {
      page.cover = { ...page.cover, ...patch.cover }
      s.cover = { ...s.cover, ...patch.cover }
      s.deck.cover = { ...s.cover }
    }
    if (patch.figure) page.figure = { ...page.figure, ...patch.figure }
    return Promise.resolve(JSON.parse(JSON.stringify(page)))
  },

  patchSkin(projectId, body) {
    const s = ensure(projectId)
    if (body.theme) s.theme = body.theme
    if (body.layout_family) s.layout_family = body.layout_family
    if (body.master) s.master = body.master
    if (s.deck) {
      s.deck.theme = s.theme
      s.deck.layout_family = s.layout_family
      s.deck.master = s.master
    }
    return Promise.resolve(statusPayload(projectId))
  },

  syncBiz(projectId) {
    const s = ensure(projectId)
    if (!s.deck) {
      return Promise.reject({ response: { status: 404, data: { detail: '尚无答辩 PPT' } } })
    }
    let updated = 0
    let kept = 0
    for (const page of s.deck.pages) {
      if (!page.bullets) continue
      for (const b of page.bullets) {
        if (b.locked) {
          kept++
        } else {
          updated++
          if (!String(b.text || '').includes('（已按工程更新）')) {
            b.text = `${b.text}（已按工程更新）`
          }
        }
      }
    }
    s.biz_dirty = false
    s.deck.biz_dirty = false
    return Promise.resolve({
      updated,
      kept,
      message: `已更新 ${updated} 处；保留人工修改 ${kept} 处`,
      ...statusPayload(projectId),
    })
  },

  check(projectId) {
    const s = ensure(projectId)
    /** @type {import('./types.js').PptCheckItem[]} */
    const items = []
    if (!s.deck) {
      items.push({ level: 'error', code: 'no_deck', message: '尚未生成答辩 PPT' })
    } else {
      items.push({ level: 'ok', code: 'deck_ok', message: 'deck.json 结构完整' })
      if (s.biz_dirty) {
        items.push({
          level: 'error',
          code: 'biz_dirty',
          message: '业务指纹脏 · 须先按工程更新业务页',
        })
      }
      if (!s.canDownload) {
        items.push({
          level: 'error',
          code: 'gates',
          message: 'bake 门禁 overall 未通过，禁止导出',
        })
      }
      const demo = s.deck.pages.find((p) => p.role === 'demo')
      if (demo?.figure?.missing || s.missingDemoShot) {
        items.push({
          level: 'error',
          code: 'demo_shot',
          message: '演示页缺主流程界面截图（禁导出）',
        })
      }
      const lockedConflict = (s.deck.pages || []).some((p) =>
        (p.bullets || []).some((b) => b.locked && String(b.text || '').includes('冲突')),
      )
      if (lockedConflict) {
        items.push({
          level: 'warning',
          code: 'locked_conflict',
          message: '存在已锁定要点与实包可能冲突（未自动覆盖）',
        })
      }
      const long = (s.deck.pages || []).some((p) =>
        (p.bullets || []).some((b) => String(b.text || '').length > 80),
      )
      if (long) {
        items.push({ level: 'warning', code: 'verbose', message: '部分要点字数偏多' })
      }
      if (!items.some((i) => i.level === 'error')) {
        items.push({ level: 'ok', code: 'export_ok', message: '可通过导出门闩' })
      }
    }
    const hasError = items.some((i) => i.level === 'error')
    return Promise.resolve({
      items,
      can_export: !hasError && !!s.deck && !s.biz_dirty && !!s.canDownload,
    })
  },

  /** mock 导出：生成占位 pptx 文本 blob URL（真实后端返回文件流） */
  exportBlob(projectId) {
    const s = ensure(projectId)
    const name = `${s.title || 'defense'}-答辩.pptx`
    const blob = new Blob(
      [`[mock PPTX placeholder]\nproject=${projectId}\ntheme=${s.theme}\npages=${s.deck?.pages?.length || 0}\n`],
      { type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' },
    )
    return { blob, filename: name }
  },

  captureScreenshot(projectId, { pageId } = {}) {
    const s = ensure(projectId)
    if (!s.deck) {
      return Promise.reject({ response: { status: 404, data: { detail: '尚无答辩 PPT' } } })
    }
    const page = s.deck.pages.find((p) => p.id === pageId) || s.deck.pages.find((p) => p.role === 'demo')
    if (page) {
      page.figure = {
        kind: 'screenshot',
        label: '主流程界面截图（已采）',
        available: true,
        missing: false,
        url: DEMO_BADGE,
      }
    }
    s.missingDemoShot = false
    return Promise.resolve({ ok: true, page_id: page?.id })
  },

  uploadScreenshot(projectId, { pageId, dataUrl } = {}) {
    const s = ensure(projectId)
    if (!s.deck) {
      return Promise.reject({ response: { status: 404, data: { detail: '尚无答辩 PPT' } } })
    }
    const page = s.deck.pages.find((p) => p.id === pageId) || s.deck.pages.find((p) => p.role === 'demo')
    if (page) {
      page.figure = {
        kind: 'screenshot',
        label: '主流程界面截图（已上传）',
        available: true,
        missing: false,
        url: dataUrl || DEMO_BADGE,
      }
    }
    s.missingDemoShot = false
    return Promise.resolve({ ok: true, page_id: page?.id })
  },

  fillDemoCover(projectId) {
    const cover = {
      school: 'XX 大学',
      college: '计算机学院',
      class_name: '软件 2201',
      student_name: '张三',
      student_id: '2022001',
      advisor: '李老师',
      badge_data_url: DEMO_BADGE,
    }
    return this.putCover(projectId, cover)
  },
}

export function resetMockPptStore() {
  for (const s of store.values()) {
    if (s.genTimer) clearInterval(s.genTimer)
  }
  store.clear()
}

export { emptyEvidence }
