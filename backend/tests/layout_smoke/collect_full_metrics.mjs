/**
 * D4 全表：按 visit plan 打开 path，mock /api，采集通用几何。
 * 单 browser + 按 role 复用 context；进度写入 LAYOUT_SMOKE_PROGRESS。
 */
import { createRequire } from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const feRoot =
  process.env.LAYOUT_SMOKE_FE_ROOT ||
  path.resolve(__dirname, '../../../../frontend')
const require = createRequire(path.join(feRoot, 'package.json'))
const { chromium } = require('playwright')

const baseURL = (process.env.LAYOUT_SMOKE_BASE_URL || 'http://127.0.0.1:5173').replace(
  /\/$/,
  '',
)
const planPath = process.env.LAYOUT_SMOKE_PLAN_PATH
const progressPath = process.env.LAYOUT_SMOKE_PROGRESS || ''
if (!planPath || !fs.existsSync(planPath)) {
  console.error('LAYOUT_SMOKE_PLAN_PATH missing')
  process.exit(2)
}
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'))
const visits = Array.isArray(plan.visits) ? plan.visits : []
const crushProbe = plan.crush_probe || null

function logProgress(msg) {
  if (!progressPath) return
  try {
    fs.appendFileSync(progressPath, `${new Date().toISOString()} ${msg}\n`, 'utf8')
  } catch (_) {}
}

async function mockApi(page, role, { mustChangePassword = false } = {}) {
  await page.route('**/*', async (route) => {
    let pathname = ''
    try {
      pathname = new URL(route.request().url()).pathname
    } catch {
      return route.continue()
    }
    if (!pathname.startsWith('/api/')) return route.continue()
    const json = (body) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(body),
      })
    if (pathname.includes('/auth/me')) {
      return json({
        code: 0,
        data: {
          username: 'smoke',
          role: role === 'user' ? 'user' : 'admin',
          nickname: '冒烟',
          superAdmin: role === 'admin',
          staffKind: role === 'staff' ? 'worker' : '',
          staffPost: '',
          mustChangePassword: !!mustChangePassword,
          mustActivateEmail: false,
          profileEditable: true,
        },
      })
    }
    if (
      pathname === '/api/profile' ||
      (pathname.includes('/api/profile') &&
        !pathname.includes('avatar') &&
        !pathname.includes('change') &&
        !pathname.includes('cancel'))
    ) {
      return json({
        code: 0,
        data: {
          username: 'smoke',
          nickname: '买家甲',
          phone: '',
          avatarUrl: '',
          profileEditable: true,
          extras: {},
          hasSecurityQuestion: false,
          realNameAcked: false,
          orgId: null,
        },
      })
    }
    if (pathname.includes('/auth/login-logs') || pathname.includes('/auth/my-sessions')) {
      return json({ code: 0, data: [] })
    }
    if (pathname.includes('/auth/captcha')) {
      return json({
        image:
          'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
        captchaKey: 'smoke',
      })
    }
    if (pathname.includes('/auth/menu-keys')) {
      return json({ code: 0, data: { keys: [], usePacks: true } })
    }
    if (pathname.includes('/meta') || pathname.includes('/site-settings')) {
      return json({
        code: 0,
        data: { title: '布局冒烟夹具', appName: '布局冒烟夹具' },
      })
    }
    if (pathname.includes('/page') || pathname.includes('/list')) {
      return json({ code: 0, data: { records: [], list: [], total: 0, rows: [] } })
    }
    return json({ code: 0, data: {} })
  })
}

async function collect(page, visit) {
  return page.evaluate((v) => {
    function b(el) {
      if (!el) return null
      const r = el.getBoundingClientRect()
      if (r.width <= 0 || r.height <= 0) return null
      return { x: r.x, y: r.y, w: r.width, h: r.height }
    }
    const app = document.querySelector('#app')
    const overlay = !!document.querySelector('vite-error-overlay')
    const text = (document.body?.innerText || '').trim()
    const chromeEl =
      document.querySelector('.admin-layout') ||
      document.querySelector('.portal-layout') ||
      document.querySelector('.work-layout') ||
      document.querySelector('header') ||
      document.querySelector('.auth')
    const ctas = [
      ...document.querySelectorAll(
        'button.el-button--primary, .el-button--primary, button.submit, a.el-button--primary',
      ),
    ]
      .map((el) => ({ box: b(el), text: (el.innerText || '').trim().slice(0, 40) }))
      .filter((x) => x.box)
      .slice(0, 8)
    let cta_full_ellipsis = false
    for (const el of document.querySelectorAll('button.el-button--primary, button.submit')) {
      const t = (el.innerText || '').trim()
      if (t.length >= 8 && el.scrollWidth > el.clientWidth + 2) {
        cta_full_ellipsis = true
        break
      }
    }
    const dialog =
      document.querySelector('.el-overlay .el-dialog') ||
      document.querySelector('.el-overlay .el-drawer') ||
      document.querySelector('.el-dialog') ||
      document.querySelector('.el-drawer')
    const dialogVisible = !!(
      dialog &&
      dialog.getBoundingClientRect().width > 0 &&
      getComputedStyle(dialog).display !== 'none'
    )
    const overflow_x =
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 2

    function edgeGap(a, c) {
      const dx = Math.max(0, Math.max(a.x - (c.x + c.w), c.x - (a.x + a.w)))
      const dy = Math.max(0, Math.max(a.y - (c.y + c.h), c.y - (a.y + a.h)))
      if (dx === 0 && dy === 0) return 0
      if (dx === 0) return dy
      if (dy === 0) return dx
      return Math.sqrt(dx * dx + dy * dy)
    }
    /** 绝对/固定定位可点：量到同一定位宿主里最近文档流子块的间距 */
    const abs_ctrls = []
    const clickables = document.querySelectorAll(
      'button, a.el-button, button.el-button, .el-button, [role="button"]',
    )
    for (const el of clickables) {
      if (abs_ctrls.length >= 16) break
      let posEl = el
      while (posEl && posEl !== document.body) {
        const st = getComputedStyle(posEl)
        if (st.position === 'absolute' || st.position === 'fixed') break
        posEl = posEl.parentElement
      }
      if (!posEl || posEl === document.body) continue
      const pst = getComputedStyle(posEl)
      if (pst.position !== 'absolute' && pst.position !== 'fixed') continue
      const ctrlBox = b(el)
      if (!ctrlBox) continue
      const host = posEl.offsetParent || posEl.parentElement
      if (!host) continue
      let best = Infinity
      for (const kid of host.children) {
        if (kid === posEl || kid.contains(el) || posEl.contains(kid)) continue
        const ks = getComputedStyle(kid)
        if (ks.position === 'absolute' || ks.position === 'fixed') continue
        if (ks.display === 'none') continue
        const kb = b(kid)
        if (!kb) continue
        const g = edgeGap(ctrlBox, kb)
        if (g < best) best = g
      }
      if (best === Infinity) continue
      let nearest = null
      for (const kid of host.children) {
        if (kid === posEl || kid.contains(el) || posEl.contains(kid)) continue
        const ks = getComputedStyle(kid)
        if (ks.position === 'absolute' || ks.position === 'fixed') continue
        if (ks.display === 'none') continue
        const kb = b(kid)
        if (!kb) continue
        if (edgeGap(ctrlBox, kb) === best) {
          nearest = kb
          break
        }
      }
      const cx = ctrlBox.x + ctrlBox.w / 2
      const ax = nearest ? nearest.x + nearest.w / 2 : null
      abs_ctrls.push({
        gap: best,
        cx_delta: ax == null ? null : Math.abs(cx - ax),
        text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 24),
        tag: (el.tagName || '').toLowerCase(),
      })
    }

    return {
      visit_id: v.visit_id,
      want_path: v.path,
      path: location.pathname,
      href: location.href,
      not_blank: !overlay && !!app && text.length >= 8,
      overlay,
      text_len: text.length,
      root: b(app),
      chrome: b(chromeEl),
      ctas,
      cta: ctas[0]?.box || null,
      cta_full_ellipsis,
      overflow_x,
      dialog_open: dialogVisible,
      dialog: dialogVisible ? b(dialog) : null,
      auth: b(document.querySelector('.auth')),
      panel: b(document.querySelector('.auth .panel')),
      brand: b(document.querySelector('.auth .brand')),
      footer: b(document.querySelector('.auth .panel-ft')),
      expect_footer: !!v.expect_footer,
      abs_ctrls,
    }
  }, visit)
}

async function launchBrowser() {
  const attempts = [
    { headless: true },
    { headless: true, channel: 'chrome' },
    { headless: true, channel: 'msedge' },
  ]
  let lastErr
  for (const opts of attempts) {
    try {
      return await chromium.launch(opts)
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr
}

function applyAuthScript() {
  return ({ role: r, delivered: d, mustChangePassword: mustPw }) => {
    globalThis.__LAYOUT_SMOKE_DELIVERED__ = d || {}
    localStorage.clear()
    if (r === 'none' || r === 'auth') return
    localStorage.setItem('token', 'smoke-token')
    localStorage.setItem('username', 'smoke')
    localStorage.setItem('nickname', '冒烟')
    if (mustPw) localStorage.setItem('mustChangePassword', '1')
    else localStorage.removeItem('mustChangePassword')
    if (r === 'user') {
      localStorage.setItem('role', 'user')
      localStorage.setItem('superAdmin', 'false')
      localStorage.setItem('staffKind', '')
    } else if (r === 'staff') {
      localStorage.setItem('role', 'admin')
      localStorage.setItem('superAdmin', 'false')
      localStorage.setItem('staffKind', 'worker')
    } else {
      localStorage.setItem('role', 'admin')
      localStorage.setItem('superAdmin', 'true')
      localStorage.setItem('staffKind', '')
    }
  }
}

async function openContext(
  browser,
  role,
  delivered,
  { crush = false, mustChangePassword = false } = {},
) {
  const viewport = crush
    ? { width: 390, height: 844 }
    : { width: 1280, height: 800 }
  const context = await browser.newContext({ viewport })
  await context.addInitScript(applyAuthScript(), {
    role,
    delivered: delivered || {},
    mustChangePassword: !!mustChangePassword,
  })
  const page = await context.newPage()
  const apiRole = role === 'none' || role === 'auth' ? 'user' : role
  await mockApi(page, apiRole, { mustChangePassword })
  page._smokePageErrors = []
  page.on('pageerror', (err) => {
    page._smokePageErrors.push(String(err.message || err))
  })
  return {
    context,
    page,
    role,
    mustPw: !!mustChangePassword,
    deliveredKey: JSON.stringify(delivered || {}),
  }
}

async function runVisitOnPage(page, visit, { crush = false } = {}) {
  // 同 context 内切换皮：写 Proxy 覆盖后再导航（模块重载后读新值）
  await page.evaluate((d) => {
    globalThis.__LAYOUT_SMOKE_DELIVERED__ = d || {}
  }, visit.delivered || {})

  const target = `${baseURL}${visit.path}`
  let nav_error = ''
  try {
    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(crush ? 120 : 180)
  } catch (err) {
    nav_error = String(err.message || err)
  }
  if (crush && visit.crush_cta) {
    try {
      await page.evaluate(() => {
        const cta =
          document.querySelector('button.el-button.submit') ||
          document.querySelector('button.el-button--primary') ||
          document.querySelector('.submit')
        if (cta) {
          cta.textContent =
            '确认登录并进入系统主工作台立即办理全部业务请点击此处超长标签挤压探针'
        }
      })
      await page.waitForTimeout(60)
    } catch (_) {}
  }
  if (visit.try_dialog) {
    try {
      const candidates = page.locator(
        'button:has-text("新增"), button:has-text("新建"), button:has-text("编辑"), button:has-text("详情"), button:has-text("查看"), .el-button--primary',
      )
      const n = Math.min(await candidates.count(), 3)
      for (let i = 0; i < n; i++) {
        try {
          await candidates.nth(i).click({ timeout: 500 })
          await page.waitForTimeout(120)
          if ((await page.locator('.el-dialog, .el-drawer').count()) > 0) break
        } catch (_) {}
      }
    } catch (_) {}
  }
  let metrics
  try {
    metrics = await collect(page, visit)
  } catch (err) {
    metrics = {
      visit_id: visit.visit_id,
      want_path: visit.path,
      not_blank: false,
      overlay: true,
      collect_error: String(err.message || err),
    }
  }
  metrics.crush = crush
  metrics.nav_error = nav_error
  metrics.page_errors = page._smokePageErrors || []
  page._smokePageErrors = []
  return metrics
}

const browser = await launchBrowser()
const results = []
let slot = null
try {
  logProgress(`start visits=${visits.length}`)
  for (let i = 0; i < visits.length; i++) {
    const visit = visits[i]
    const role = visit.role || 'user'
    const mustPw = !!visit.must_change_password
    if (!slot || slot.role !== role || slot.mustPw !== mustPw) {
      if (slot) await slot.context.close()
      slot = await openContext(browser, role, visit.delivered || {}, {
        mustChangePassword: mustPw,
      })
    }
    const metrics = await runVisitOnPage(slot.page, visit, { crush: false })
    results.push(metrics)
    if ((i + 1) % 20 === 0 || i === visits.length - 1) {
      logProgress(`done ${i + 1}/${visits.length} last=${visit.visit_id}`)
    }
  }
  if (slot) {
    await slot.context.close()
    slot = null
  }
  if (crushProbe && crushProbe.path) {
    slot = await openContext(browser, crushProbe.role || 'none', {}, { crush: true })
    const metrics = await runVisitOnPage(
      slot.page,
      { ...crushProbe, crush_cta: true },
      { crush: true },
    )
    metrics.crush_probe = true
    results.push(metrics)
    logProgress('crush_probe done')
  }
} finally {
  if (slot) {
    try {
      await slot.context.close()
    } catch (_) {}
  }
  await browser.close()
}

logProgress(`finish count=${results.length}`)
console.log(JSON.stringify({ ok: true, count: results.length, results }))
