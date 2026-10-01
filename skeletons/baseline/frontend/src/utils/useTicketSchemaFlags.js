import { computed } from 'vue'
import { getSchema, ticketCopy, archiveCopy, hasCap } from './domainSchema.js'

/**
 * 单据页共用的 schema 派生旗标（MyTickets / ArchiveBrowse 对齐）。
 * 必须在 setup 内调用，勿缓存成 build-time 常量。
 */
export function useTicketSchemaFlags() {
  const ticket = ticketCopy()
  const archive = archiveCopy()
  const verbs = computed(() => ticket.verbs || {})
  const states = computed(() => ticket.states || {})
  const labels = computed(() => getSchema()?.labels || {})
  const caps = computed(() => getSchema()?.capabilities || [])

  const applyFromList = computed(() => !!ticket.applyFromList)
  const autoApprove = computed(() => !!ticket.autoApprove)
  const requireAttach = computed(() => !!ticket.requireAttach)
  const requireMaterial = computed(() => !!ticket.requireMaterialChecklist)
  const requireRemark = computed(() => !!ticket.requireRemark)
  const remarkLabel = computed(() => ticket.remarkLabel || '说明')
  const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
  const pickDateRange = computed(() => !!ticket.pickDateRange)
  const allowQty = computed(() => !!ticket.allowQty)
  const qtyMax = computed(() => {
    const n = Number(ticket.qtyMax)
    return Number.isFinite(n) && n > 0 ? n : 99
  })
  const matchProfileRoom = computed(() => !!ticket.matchProfileRoom)
  const matchProfileOpts = computed(() => ({
    buildingKey: ticket.matchProfileBuildingKey || 'dormBuilding',
    roomKey: ticket.matchProfileRoomKey || 'dormRoom',
    buildingField: ticket.matchProfileBuildingField || 'author',
    roomField: ticket.matchProfileRoomField || 'title',
    looseBuilding: !!ticket.matchProfileLooseBuilding,
  }))
  const matchProfileNeedMessage = computed(
    () => ticket.matchProfileNeedMessage || '请先在个人资料填写楼栋与房间',
  )
  const matchProfileDenyMessage = computed(
    () => ticket.matchProfileDenyMessage || '只能对本寝室的查寝场次登记归寝',
  )
  const filterByOwnerToken = computed(() => !!ticket.filterByOwnerToken)
  const ownerTokenSource = computed(() => ticket.ownerTokenSource || 'phone')
  const ownerTokenStrict = computed(() => !!ticket.ownerTokenStrict)
  const requireClaimCode = computed(() => !!ticket.requireClaimCode)
  const allowProxyPickup = computed(() => !!ticket.allowProxyPickup)
  const allowDeposit = computed(() => !!ticket.allowDeposit)
  const requireNoticeAck = computed(() => !!ticket.requireNoticeAck)
  const requireTrainingAck = computed(() => !!ticket.requireTrainingAck)
  const requireInsuranceAck = computed(() => !!ticket.requireInsuranceAck)
  const requireMeetingAck = computed(() => !!ticket.requireMeetingAck)
  const requireApplyInvite = computed(() => !!ticket.requireApplyInvite)
  const requirePriceNoteAck = computed(() => !!ticket.requirePriceNoteAck)
  const requireSponsorAck = computed(() => !!ticket.requireSponsorAck)
  const requirePlanAck = computed(() => !!ticket.requirePlanAck)
  const requirePrereqAck = computed(() => !!ticket.requirePrereqAck)
  const requirePeerConfirm = computed(() => !!ticket.requirePeerConfirm)
  const allowEmergencyContact = computed(() => !!ticket.allowEmergencyContact)
  const allowMeetingPlace = computed(() => !!ticket.allowMeetingPlace)
  const richRemark = computed(() => !!ticket.richRemark)
  const multiApproveOn = computed(() => hasCap('multi_approve'))
  const archiveLabel = computed(() => archive.label || '事项')
  const archiveMode = computed(() => caps.value.includes('archive'))
  const applyVerb = computed(() => verbs.value.apply || '提交')

  return {
    ticket,
    archive,
    verbs,
    states,
    labels,
    caps,
    applyFromList,
    autoApprove,
    requireAttach,
    requireMaterial,
    requireRemark,
    remarkLabel,
    pickLoanPeriod,
    pickDateRange,
    allowQty,
    qtyMax,
    matchProfileRoom,
    matchProfileOpts,
    matchProfileNeedMessage,
    matchProfileDenyMessage,
    filterByOwnerToken,
    ownerTokenSource,
    ownerTokenStrict,
    requireClaimCode,
    allowProxyPickup,
    allowDeposit,
    requireNoticeAck,
    requireTrainingAck,
    requireInsuranceAck,
    requireMeetingAck,
    requireApplyInvite,
    requirePriceNoteAck,
    requireSponsorAck,
    requirePlanAck,
    requirePrereqAck,
    requirePeerConfirm,
    allowEmergencyContact,
    allowMeetingPlace,
    richRemark,
    multiApproveOn,
    archiveLabel,
    archiveMode,
    applyVerb,
  }
}
