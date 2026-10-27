/**
 * D3 试点：/login（AuthShell）+ /profile×member（换头像贴圆）。
 * stdout 最后一行 JSON；由 layout_smoke.run_playwright_pilot 消费。
 */
import { createRequire } from 'node:module'
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
const crush = process.env.LAYOUT_SMOKE_CRUSH === '1'
const viewport = crush ? { width: 390, height: 844 } : { width: 1280, height: 800 }

const MEMBER_DELIVERED = {
  domainGroup: 'trade',
  shellNavStyle: 'storefront',
  tradeSurfaceStyle: 'shelfgrid',
}

async function mockApi(page) {
  await page.route('**/*', async (route) => {
    let pathname = ''
    try {
      pathname = new URL(route.request().url()).pathname
    } catch {
      return route.continue()
    }
    if (!pathname.startsWith('/api/')) {
      return route.continue()
    }
    const json = (body) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(body),
      })
    const u = route.request().url()
    if (u.includes('/auth/captcha')) {
      return json({
        image:
          'data:image/png;base64,iVBORw0KGgoAAAANSUhUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
        captchaKey: 'smoke',
      })
    }
    if (u.includes('/auth/me')) {
      return json({
        code: 0,
        data: {
          username: 'smoke',
          role: 'user',
          nickname: '冒烟',
          superAdmin: false,
          profileEditable: true,
          mustChangePassword: false,
        },
      })
    }
    if (u.includes('/api/profile') && !u.includes('avatar') && !u.includes('change')) {
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
    if (u.includes('/meta') || u.includes('/site-settings')) {
      return json({ title: '布局冒烟夹具', appName: '布局冒烟夹具' })
    }
    if (u.includes('/auth/login-logs') || u.includes('/auth/my-sessions')) {
      return json({ code: 0, data: [] })
    }
    if (u.includes('/loyalty/me')) {
      return json({ code: 0, data: null })
    }
    return json({ code: 0, data: {} })
  })
}

async function collectLogin(page) {
  return page.evaluate(() => {
    const auth = document.querySelector('.auth')
    const panel = document.querySelector('.auth .panel')
    const brand = document.querySelector('.auth .brand')
    const footer = document.querySelector('.auth .panel-ft')
    const cta =
      document.querySelector('.auth button.el-button.submit') ||
      document.querySelector('.auth .submit') ||
      document.querySelector('.auth button.el-button--primary')

    function b(el) {
      if (!el) return null
      const r = el.getBoundingClientRect()
      if (r.width <= 0 || r.height <= 0) return null
      return { x: r.x, y: r.y, w: r.width, h: r.height }
    }

    let cta_full_ellipsis = false
    if (cta) {
      const text = (cta.innerText || '').trim()
      if (text.length >= 8 && cta.scrollWidth > cta.clientWidth + 2) {
        cta_full_ellipsis = true
      }
    }

    return {
      not_blank: !!(auth && (panel || cta)),
      expect_footer: true,
      auth: b(auth),
      panel: b(panel),
      brand: b(brand),
      footer: b(footer),
      cta: b(cta),
      cta_full_ellipsis,
      cta_text: cta ? (cta.innerText || '').trim() : '',
    }
  })
}

async function collectProfile(page) {
  return page.evaluate(() => {
    function b(el) {
      if (!el) return null
      const r = el.getBoundingClientRect()
      if (r.width <= 0 || r.height <= 0) return null
      return { x: r.x, y: r.y, w: r.width, h: r.height }
    }
    function edgeGap(a, c) {
      const dx = Math.max(0, Math.max(a.x - (c.x + c.w), c.x - (a.x + a.w)))
      const dy = Math.max(0, Math.max(a.y - (c.y + c.h), c.y - (a.y + a.h)))
      if (dx === 0 && dy === 0) return 0
      if (dx === 0) return dy
      if (dy === 0) return dx
      return Math.sqrt(dx * dx + dy * dy)
    }
    const slot = document.querySelector('.avatar-slot')
    const text = (document.body?.innerText || '').trim()
    const faceHost = document.querySelector('[data-account-face]')
    const abs_ctrls = []
    for (const el of document.querySelectorAll(
      'button, a.el-button, button.el-button, .el-button, [role="button"]',
    )) {
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
        text: (el.innerText || '').trim().slice(0, 24),
        tag: (el.tagName || '').toLowerCase(),
      })
    }
    return {
      not_blank: text.length >= 8 && !!slot,
      path: location.pathname,
      account_face: faceHost ? faceHost.getAttribute('data-account-face') || '' : '',
      abs_ctrls,
    }
  })
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

const browser = await launchBrowser()
const context = await browser.newContext({ viewport })
const page = await context.newPage()
try {
  await mockApi(page)
  page.on('pageerror', (err) => {
    console.error('PAGEERR', err.message)
  })

  await page.goto(`${baseURL}/login`, {
    waitUntil: 'networkidle',
    timeout: 60000,
  })
  try {
    await page.waitForSelector('.auth', { timeout: 30000 })
  } catch (err) {
    const overlay = await page.locator('vite-error-overlay').count()
    const body = await page.locator('body').innerHTML()
    throw new Error(
      `等待 .auth 超时 overlay=${overlay} url=${page.url()} body=${body.slice(0, 800)}`,
    )
  }
  if (crush) {
    await page.evaluate(() => {
      const cta =
        document.querySelector('.auth button.el-button.submit') ||
        document.querySelector('.auth .submit')
      if (cta) {
        cta.textContent =
          '确认登录并进入系统主工作台立即办理全部业务请点击此处超长标签挤压探针'
      }
    })
    await page.waitForTimeout(100)
  }
  const login = await collectLogin(page)

  await page.evaluate((delivered) => {
    globalThis.__LAYOUT_SMOKE_DELIVERED__ = delivered || {}
    localStorage.setItem('token', 'smoke-token')
    localStorage.setItem('username', 'smoke')
    localStorage.setItem('nickname', '冒烟')
    localStorage.setItem('role', 'user')
    localStorage.setItem('superAdmin', 'false')
    localStorage.removeItem('mustChangePassword')
  }, MEMBER_DELIVERED)
  await page.goto(`${baseURL}/profile`, {
    waitUntil: 'networkidle',
    timeout: 60000,
  })
  try {
    await page.waitForSelector('.avatar-slot', { timeout: 30000 })
  } catch (err) {
    const body = await page.locator('body').innerHTML()
    throw new Error(`等待 .avatar-slot 超时 url=${page.url()} body=${body.slice(0, 800)}`)
  }
  await page.waitForTimeout(200)
  const profile = await collectProfile(page)

  const metrics = {
    ...login,
    crush,
    viewport,
    profile_member: profile,
  }
  console.log(JSON.stringify(metrics))
} finally {
  await browser.close()
}
