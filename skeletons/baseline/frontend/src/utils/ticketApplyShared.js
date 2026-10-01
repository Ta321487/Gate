/**
 * 单据申请共用：空表单默认值 + 提交成功文案。
 * MyTickets（list）与 ArchiveBrowse（browse）表单结构不同，仅共享可对齐片段。
 */

/** MyTickets applyFromList / standalone 共用的 reactive 初始字段 */
export function createEmptyTicketApplyForm() {
  return {
    title: '',
    location: '',
    remark: '',
    attachUrl: '',
    typeId: null,
    siteId: null,
    roomId: null,
    itemId: null,
    period: null,
    contactChannel: '',
    nextFollowAt: '',
    weekNo: null,
    interviewPlace: '',
    priority: '普通',
    contactPhone: '',
    proxyName: '',
    proxyPhone: '',
    depositYuan: null,
    pickupPlace: '',
    emergencyContact: '',
    emergencyPhone: '',
    noticeAck: false,
    trainingAck: false,
    insuranceAck: false,
    meetingAck: false,
    inviteCode: '',
    priceNoteAck: false,
    sponsorAck: false,
    planAck: false,
    prereqAck: false,
    projectNo: '',
    procureRefNo: '',
    dualReviewerA: '',
    dualReviewerB: '',
    shipFeeYuan: null,
    utilityNote: '',
    peerUsername: '',
    interviewResult: '',
    writtenScore: null,
    bgCheckNote: '',
    dealAmountYuan: null,
    nextAction: '',
    nextActionDone: false,
    returnDate: '',
    defenseResult: '',
    bankAccount: '',
    homeVisitFamily: '',
    homeVisitTalk: '',
    homeVisitPlan: '',
    feedbackInterest: '',
    feedbackConcern: '',
    feedbackNext: '',
    recordUrl: '',
    appraisalComment: '',
    appraisalGrade: '',
    companyEval: '',
    preferredSlot: '',
    addressType: '',
    nightUrgent: false,
    assetCode: '',
    subscribeProgress: false,
    audioUrl: '',
    confidential: false,
    assignDept: '',
    resumeEdu: '',
    resumeExp: '',
    resumeSkill: '',
  }
}

/**
 * 申请接口成功后的站内提示（候补 / 预约 / 签到 / 自动通过）。
 * @param {object} data POST /api/tickets/apply 响应体（或 data.data）
 * @param {{ autoApprove?: boolean, checkinOnApply?: boolean, applyVerb?: string, getSchema?: () => any }} opts
 */
export function formatTicketApplySuccess(data, opts = {}) {
  const st = data?.status || data?.data?.status
  const schema = typeof opts.getSchema === 'function' ? opts.getSchema() : null
  const labels = schema?.labels || {}
  if (st === 'held') {
    return labels.bookHoldOkMessage || '暂无库存，已加入预约队列'
  }
  if (st === 'waitlisted') {
    const rank = data?.waitlistRank || data?.waitlistPos || data?.queueNo
    if (rank) return `名额已满，已加入候补（约第 ${rank} 位）`
    return labels.waitlistOkMessage || '名额已满，已加入候补队列'
  }
  if (opts.checkinOnApply) return '已签到'
  if (opts.autoApprove) return `已${opts.applyVerb || '提交'}`
  return '已提交，等待审核'
}
