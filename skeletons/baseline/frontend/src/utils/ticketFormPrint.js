/**
 * 审批域套打/公文打印：共用开窗壳，四套版式分家（证明/用印表/中期检查/伦理意见书）。
 * ≠ 电子签章平台、≠ 真 PDF 套打引擎；浏览器打印即可。
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
  return s ? esc(s) : '__________'
}

function openPrintHtml(html) {
  const w = window.open('', '_blank')
  if (!w) return false
  w.document.write(html)
  w.document.close()
  return true
}

/** 共用纸面基础样式：仿宋公文感，无卡片无渐变。 */
const BASE_CSS = `
@page { size: A4; margin: 2cm; }
body {
  margin: 0; padding: 0;
  color: #111;
  font-family: "SimSun", "Songti SC", "STSong", serif;
  font-size: 14px; line-height: 1.7;
}
.doc { max-width: 680px; margin: 0 auto; }
.org { text-align: center; font-size: 20px; font-weight: bold; letter-spacing: 2px; }
.subtitle { text-align: center; font-size: 18px; font-weight: bold; margin: 8px 0 4px; }
.meta { text-align: right; font-size: 12px; color: #333; margin-bottom: 12px; }
.rule { border: none; border-top: 1px solid #111; margin: 8px 0 16px; }
.para { text-indent: 2em; margin: 10px 0; }
.sign { margin-top: 48px; text-align: right; padding-right: 24px; }
.sign p { margin: 4px 0; }
.blank { display: inline-block; min-width: 6em; border-bottom: 1px solid #111; }
table.form { width: 100%; border-collapse: collapse; margin: 12px 0; }
table.form th, table.form td {
  border: 1px solid #111; padding: 8px 10px; vertical-align: top; text-align: left;
}
table.form th { width: 28%; font-weight: normal; background: transparent; }
.box { border: 1px solid #111; min-height: 88px; padding: 10px; margin: 8px 0 16px; }
.check { margin: 6px 0; }
.muted { font-size: 12px; color: #444; }
`

function wrapDoc(title, bodyHtml) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title>
<style>${BASE_CSS}</style></head><body>
<div class="doc">${bodyHtml}</div>
<script>window.onload=function(){window.print()}<\/script>
</body></html>`
}

function orgName(labels) {
  return labels.formOrgName || labels.schoolName || '本校'
}

/** 证明书：正文叙述体，少表格。 */
function buildCertForm(row, ctx) {
  const { labels, personLabel } = ctx
  const org = orgName(labels)
  const title = labels.printTicketLabel || '在读证明'
  const person = personLabel ? personLabel(row, '') : (row.username || '')
  const issueNo = row.certIssueNo || row.pickupRedeemCode || row.verifyCode || row.id
  const body = `
<div class="org">${esc(org)}</div>
<div class="subtitle">${esc(title)}</div>
<div class="meta">编号：${esc(issueNo)}</div>
<hr class="rule" />
<p class="para">兹证明 <span class="blank">${dash(person)}</span>（学号/工号见系统登记）确系我校学生（或教职工）。</p>
<p class="para">证明用途：${dash(row.typeName || row.title)}。申请说明：${dash(row.remark)}。</p>
<p class="para">特此证明。</p>
${row.issueCopies != null ? `<p class="para">本件开具 ${esc(row.issueCopies)} 份。</p>` : ''}
${row.pickupMethod ? `<p class="muted">领取方式：${esc(row.pickupMethod)}${row.mailAddress ? ` · ${esc(row.mailAddress)}` : ''}</p>` : ''}
<div class="sign">
  <p>${esc(org)}（盖章）</p>
  <p>经办人：<span class="blank"></span></p>
  <p>日期：${dash((row.approveAt || row.applyAt || '').toString().slice(0, 10))}</p>
</div>`
  return wrapDoc(title, body)
}

/** 用印审批登记表：全表格式。 */
function buildSealForm(row, ctx) {
  const { labels, personLabel, statusText } = ctx
  const org = orgName(labels)
  const title = labels.printTicketLabel || '印章使用审批单'
  const person = personLabel ? personLabel(row, '') : (row.username || '')
  const st = statusText ? statusText(row) : (row.status || '')
  const body = `
<div class="org">${esc(org)}</div>
<div class="subtitle">${esc(title)}</div>
<div class="meta">单据号：${esc(row.id)}</div>
<table class="form">
  <tr><th>用印事由</th><td>${dash(row.title)}</td></tr>
  <tr><th>申请人</th><td>${dash(person)}</td></tr>
  <tr><th>用印份数</th><td>${row.sealCopies != null ? esc(row.sealCopies) : '__________'} 份</td></tr>
  <tr><th>装订说明</th><td>${dash(row.bindNote)}</td></tr>
  <tr><th>用印份号</th><td>${dash(row.sealCopyNos)}</td></tr>
  <tr><th>监印确认</th><td>${row.sealWitnessAck ? '☑ 监印人已确认' : '☐ 监印人确认　　签字：__________'}</td></tr>
  <tr><th>办理状态</th><td>${dash(st)}</td></tr>
  <tr><th>备注</th><td>${dash(row.remark)}</td></tr>
</table>
<p class="muted">现场照片等材料以系统登记为准；本件仅作台账留存。</p>
<div class="sign">
  <p>用印部门（盖章）</p>
  <p>日期：${dash((row.returnAt || row.approveAt || '').toString().slice(0, 10))}</p>
</div>`
  return wrapDoc(title, body)
}

/** 大创中期检查表：项目信息 + 检查意见框。 */
function buildProjMidForm(row, ctx) {
  const { labels, personLabel } = ctx
  const org = orgName(labels)
  const title = labels.printTicketLabel || '大学生创新创业训练计划中期检查表'
  const person = personLabel ? personLabel(row, '') : (row.username || '')
  const body = `
<div class="org">${esc(org)}</div>
<div class="subtitle">${esc(title)}</div>
<div class="meta">项目登记号：${esc(row.id)}</div>
<table class="form">
  <tr><th>项目名称</th><td>${dash(row.title)}</td></tr>
  <tr><th>负责人</th><td>${dash(person)}</td></tr>
  <tr><th>成员变更说明</th><td>${dash(row.memberChangeNote)}</td></tr>
  <tr><th>经费使用（元）</th><td>${row.fundUseYuan != null ? esc(row.fundUseYuan) : '__________'}　${dash(row.fundUseNote)}</td></tr>
  <tr><th>查重材料</th><td>${dash(row.plagiarismUrl)}</td></tr>
  <tr><th>中期进展简述</th><td>${dash(row.remark)}</td></tr>
</table>
<p><strong>检查意见</strong></p>
<div class="box">${dash(row.changeLogNote)}<br/><br/></div>
<p class="check">☐ 按计划推进　　☐ 需整改后复检　　☐ 建议终止</p>
<div class="sign">
  <p>指导教师：<span class="blank"></span></p>
  <p>学院意见：<span class="blank"></span></p>
  <p>日期：${dash((row.approveAt || row.applyAt || '').toString().slice(0, 10))}</p>
</div>`
  return wrapDoc(title, body)
}

/** 伦理审查意见书：文号 + 结论框。 */
function buildEthicOpinion(row, ctx) {
  const { labels, personLabel } = ctx
  const org = orgName(labels)
  const title = labels.printTicketLabel || '伦理审查意见书'
  const person = personLabel ? personLabel(row, '') : (row.username || '')
  const batchNo = row.batchNo || row.ethicBatchNo || row.id
  const body = `
<div class="org">${esc(org)}医学/科研伦理委员会</div>
<div class="subtitle">${esc(title)}</div>
<div class="meta">批件编号：${esc(batchNo)}</div>
<hr class="rule" />
<p class="para">课题名称：${dash(row.title)}</p>
<p class="para">申请人：${dash(person)}</p>
<p class="para">会议决议摘要：${dash(row.resolutionNote || row.meetingResolve || row.remark)}</p>
<p><strong>审查意见</strong></p>
<div class="box">
<p class="check">☐ 同意　　☐ 修改后同意　　☐ 不同意</p>
<p>具体说明：</p>
<p>${dash(row.remark)}</p>
</div>
${row.expireOn || row.ethicExpireOn ? `<p class="muted">批件有效期至：${esc(row.expireOn || row.ethicExpireOn)}</p>` : ''}
<div class="sign">
  <p>${esc(org)}伦理委员会（盖章）</p>
  <p>主任委员：<span class="blank"></span></p>
  <p>日期：${dash((row.approveAt || row.meetingOn || '').toString().slice(0, 10))}</p>
</div>`
  return wrapDoc(title, body)
}

/** 报修/活动等原有通用打印，保留字段清单风格以免改坏已齐域。 */
function buildGenericForm(row, ctx) {
  const { labels, ticket, statusText, personLabel, remarkText } = ctx
  const noun = labels.printTicketLabel || ticket?.label || '工单'
  const hint = labels.activityProofHint || labels.gradePrintHint || labels.bedPrintHint
    || labels.closedStackPrintHint || labels.equipQrPrintHint || ''
  const st = statusText ? statusText(row) : (row.status || '')
  const person = personLabel ? personLabel(row, '') : (row.username || '')
  const remark = remarkText ? remarkText(row.remark) : (row.remark || '—')
  const lines = [
    hint ? `<p class="muted">${esc(hint)}</p>` : '',
    `<p>标题：${esc(row.title || '—')}</p>`,
    `<p>地点：${esc(row.location || '—')}</p>`,
    `<p>状态：${esc(st)}</p>`,
    `<p>申请人：${esc(person)}</p>`,
    row.assigneeUsername ? `<p>处理人：${esc(row.assigneeUsername)}</p>` : '',
    row.companionNames ? `<p>同行人：${esc(row.companionNames)}</p>` : '',
    row.pickupMethod ? `<p>领取方式：${esc(row.pickupMethod)}${row.mailAddress ? ` · ${esc(row.mailAddress)}` : ''}${row.certUrgent ? ' · 加急' : ''}</p>` : '',
    row.sealCopies != null ? `<p>用印份数：${esc(row.sealCopies)}${row.bindNote ? ` · ${esc(row.bindNote)}` : ''}</p>` : '',
    row.invoiceCount != null || row.fineYuan > 0
      ? `<p>发票：${row.invoiceCount != null ? `${esc(row.invoiceCount)} 张` : ''}${row.fineYuan > 0 ? ` · ${esc(row.fineYuan)} 元` : ''}</p>`
      : '',
    row.visitorCount != null ? `<p>随行人数：${esc(row.visitorCount)}</p>` : '',
    row.mileageKm != null ? `<p>里程：${esc(row.mileageKm)}${row.fuelNote ? ` · ${esc(row.fuelNote)}` : ''}</p>` : '',
    `<p>期望上门：${esc(row.preferredSlot || '—')}</p>`,
    `<p>响应时限：${esc(row.responseDueAt || '—')}</p>`,
    `<p>完结时限：${esc(row.dueAt || '—')}</p>`,
    `<p>说明：${esc(remark)}</p>`,
  ].filter(Boolean)
  const body = `<h1 style="font-size:18px;font-family:sans-serif">${esc(noun)} #${esc(row.id)}</h1>${lines.join('\n')}`
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(noun)} ${esc(row.id)}</title>
<style>body{font-family:sans-serif;padding:24px;color:#111}p{margin:6px 0}.muted{color:#64748b;font-size:12px}</style>
</head><body>${body}
<script>window.onload=function(){window.print()}<\/script>
</body></html>`
}

export function resolveFormPrintKind(ticket = {}) {
  if (ticket.allowCertFormPrint) return 'cert'
  if (ticket.allowSealFormPrint) return 'seal'
  if (ticket.allowProjMidFormPrint) return 'proj_mid'
  if (ticket.allowEthicOpinionPrint) return 'ethic'
  return 'generic'
}

const BUILDERS = {
  cert: buildCertForm,
  seal: buildSealForm,
  proj_mid: buildProjMidForm,
  ethic: buildEthicOpinion,
  generic: buildGenericForm,
}

/**
 * @returns {boolean} 是否成功打开打印窗
 */
export function printTicketDocument(row, ctx = {}) {
  if (!row) return false
  const kind = resolveFormPrintKind(ctx.ticket || {})
  const build = BUILDERS[kind] || buildGenericForm
  const html = build(row, ctx)
  return openPrintHtml(html)
}
