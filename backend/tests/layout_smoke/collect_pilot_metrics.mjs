/**
 * D3 试点：打开 /login，mock /api，采集 AuthShell + 主 CTA 几何。
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

async function mockApi(page) {
  // 只挡后端 /api/*；禁止误伤 Vite 模块 /src/api/*.js
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
    const u = route.request().url()
    if (u.includes('/auth/captcha')) {
      const png =
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ image: png, captchaKey: 'smoke' }),
      })
    }
    if (u.includes('/meta')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ title: '布局冒烟夹具', appName: '布局冒烟夹具' }),
      })
    }
    if (u.includes('/site-settings')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{}',
    })
  })
}

async function collect(page) {
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
  const metrics = await collect(page)
  metrics.crush = crush
  metrics.viewport = viewport
  console.log(JSON.stringify(metrics))
} finally {
  await browser.close()
}
