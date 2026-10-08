/**
 * 订单小票：共用开窗壳，浏览器打印。≠ 热敏机驱动 / POS 外设。
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

function openPrintHtml(html) {
  const w = window.open('', '_blank')
  if (!w) return false
  w.document.write(html)
  w.document.close()
  return true
}

export function printOrderReceipt(row, ctx = {}) {
  if (!row) return false
  const labels = ctx.labels || {}
  const title = labels.orderReceiptPrintLabel || '打印小票'
  const noun = ctx.orderNoun || '订单'
  const states = ctx.states || {}
  const status = states[row.status] || row.status || ''
  const lines = Array.isArray(row.lines) ? row.lines : []
  const rows = lines
    .map((ln) => {
      const lineYuan = ln.lineYuan
      const yuan = Number(
        lineYuan == null ? (ln.priceYuan || 0) * (ln.qty || 0) : lineYuan,
      ).toFixed(2)
      const extra = [ln.specChoice, ln.customText, ln.drawTitle].filter(Boolean).join(' / ')
      return `<tr><td>${dash(ln.title)}${extra ? `<div class="muted">${esc(extra)}</div>` : ''}</td><td>${esc(ln.qty)}</td><td>¥${yuan}</td></tr>`
    })
    .join('')
  const ship = [row.receiverName, row.receiverPhone, row.addressLine].filter(Boolean).join(' ')
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title>
<style>
@page { size: A5; margin: 12mm; }
body { margin: 0; color: #111; font-family: "SimSun", "Songti SC", serif; font-size: 13px; }
h1 { font-size: 16px; text-align: center; margin: 0 0 8px; }
.meta { margin: 4px 0; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
th, td { border-bottom: 1px solid #333; padding: 4px 6px; text-align: left; }
.muted { color: #555; font-size: 12px; }
.total { text-align: right; font-weight: bold; margin-top: 8px; }
</style></head><body>
<h1>${esc(noun)}小票</h1>
<div class="meta">${esc(noun)}编号：${esc(row.id)}　状态：${dash(status)}</div>
<div class="meta">下单时间：${dash(row.createdAt)}</div>
${ship ? `<div class="meta">收货：${esc(ship)}</div>` : ''}
${row.tableNo ? `<div class="meta">${esc(ctx.tableNoLabel || '桌号')}：${esc(row.tableNo)}</div>` : ''}
${row.pickupCode ? `<div class="meta">${esc(ctx.pickupNoLabel || ctx.pickupCodeLabel || '取货码')}：${esc(row.pickupCode)}</div>` : ''}
${row.utensilOpt ? `<div class="meta">${esc(ctx.utensilOptLabel || '餐具')}：${esc(row.utensilOpt)}</div>` : ''}
${row.packOpt ? `<div class="meta">${esc(ctx.packOptLabel || '打包')}：${esc(row.packOpt)}</div>` : ''}
${row.mergeCode ? `<div class="meta">${esc(ctx.mergeCodeLabel || '拼单码')}：${esc(row.mergeCode)}</div>` : ''}
${row.etaText ? `<div class="meta">${esc(ctx.etaLabel || '预计送达')}：${esc(row.etaText)}</div>` : ''}
${Number(row.packagingFeeYuan || 0) > 0 ? `<div class="meta">${esc(ctx.packagingFeeLabel || '包装费')}：¥${Number(row.packagingFeeYuan).toFixed(2)}</div>` : ''}
${Number(row.deliveryFeeYuan || 0) > 0 ? `<div class="meta">${esc(ctx.deliveryFeeLabel || '配送费')}：¥${Number(row.deliveryFeeYuan).toFixed(2)}</div>` : ''}
${row.remark ? `<div class="meta">备注：${esc(row.remark)}</div>` : ''}
<table><thead><tr><th>明细</th><th>数量</th><th>金额</th></tr></thead>
<tbody>${rows || '<tr><td colspan="3">—</td></tr>'}</tbody></table>
<div class="total">合计 ¥${Number(row.totalYuan || 0).toFixed(2)}</div>
<script>window.onload=function(){window.print()}<\/script>
</body></html>`
  return openPrintHtml(html)
}
