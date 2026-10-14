/**
 * 订单发票打印页（浏览器开窗）。非税控电子发票通道。
 */

function esc(v) {
  return String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function dash(v) {
  const s = String(v ?? '').trim()
  return s ? esc(s) : '—'
}

export function printOrderInvoice(row, ctx = {}) {
  if (!row) return false
  const labels = ctx.labels || {}
  const title = labels.invoiceDownloadLabel || '下载发票'
  const noun = ctx.orderNoun || '订单'
  const statusMap = {
    pending: labels.invoiceStatusPending || '申请中',
    issued: labels.invoiceStatusIssued || '已开',
  }
  const st = statusMap[row.invoiceStatus] || row.invoiceStatus || '—'
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title>
<style>
@page { size: A5; margin: 14mm; }
body { margin: 0; color: #111; font-family: "SimSun", "Songti SC", serif; font-size: 13px; }
h1 { font-size: 18px; text-align: center; margin: 0 0 12px; }
.meta { margin: 6px 0; }
.muted { color: #555; font-size: 12px; margin-top: 16px; }
</style></head><body>
<h1>增值税普通发票</h1>
<div class="meta">购方名称：${dash(row.invoiceTitle)}</div>
<div class="meta">${esc(noun)}编号：${esc(row.id)}</div>
<div class="meta">金额合计：¥${Number(row.totalYuan || 0).toFixed(2)}</div>
<div class="meta">开票状态：${dash(st)}</div>
<div class="meta">下单时间：${dash(row.createdAt)}</div>
<p class="muted">${esc(labels.invoiceDownloadHint || '可用固定模板下载后打印或保存；非税控电子发票。')}</p>
<script>window.onload=function(){window.print()}<\/script>
</body></html>`
  const w = window.open('', '_blank')
  if (!w) return false
  w.document.write(html)
  w.document.close()
  return true
}
