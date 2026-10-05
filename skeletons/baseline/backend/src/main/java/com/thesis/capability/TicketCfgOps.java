package com.thesis.capability;

import java.util.*;

/**
 * TicketCfgOps：TicketStore 纯业务逻辑拆分（零 DB 接触）。
 *
 * <p>三栈共用：bake 时由 baseline 提供；mybatis/jpa overlay 不含此类
 * （helper 不出现任何 JDBC/MyBatis token，故不参与 persistence 覆盖）。
 * 对 TicketStore 静态成员的引用一律使用显式限定名。
 */
final class TicketCfgOps {

    private TicketCfgOps() {}

    /** 约定：进度表 = {单据表}_progress；可显式覆盖。 */

    public static void configureProgress(String progressTable) {
        if (progressTable != null && !progressTable.isBlank()) {
            TicketStore.PROGRESS = progressTable.trim();
        } else {
            TicketStore.bindProgressDefault();
        }
        TicketStore.ensureProgressTable();
    
    }


    public static void configureL1(boolean twoLevel, boolean attachRequired, boolean ratingEnabled) {
        TicketStore.twoLevelApprove = twoLevel || TicketStore.threeLevelApprove;
        TicketStore.requireAttach = attachRequired;
        TicketStore.allowRating = ratingEnabled;
    
    }

    /** C-16：三级会签；开启后二级路径扩展为 pending→pending_mid→pending_final */

    public static void configureThreeLevel(boolean enabled) {
        TicketStore.threeLevelApprove = enabled;
        if (enabled) {
            TicketStore.twoLevelApprove = true;
        }
    
    }

    /** C-14：审核通过扣减时长；须在 configureLoanOptions 前或后再调一次 refresh */

    public static void configureTimebankRedeem(boolean enabled) {
        TicketStore.timebankRedeem = enabled;
        if (enabled && TicketStore.MODE == TicketStore.Mode.ARCHIVE) {
            TicketStore.allowQty = true;
        }
    
    }


    public static void configureMatchProfileRoom(
            boolean enabled,
            String buildingKey,
            String roomKey,
            String buildingField,
            String roomField,
            boolean looseBuilding,
            String needMessage,
            String denyMessage) {
        TicketStore.matchProfileRoom = enabled;
        TicketStore.matchProfileBuildingKey = (buildingKey == null || buildingKey.isBlank()) ? "dormBuilding" : buildingKey.trim();
        TicketStore.matchProfileRoomKey = (roomKey == null || roomKey.isBlank()) ? "dormRoom" : roomKey.trim();
        TicketStore.matchProfileBuildingField = (buildingField == null || buildingField.isBlank()) ? "author" : buildingField.trim();
        TicketStore.matchProfileRoomField = (roomField == null || roomField.isBlank()) ? "title" : roomField.trim();
        TicketStore.matchProfileLooseBuilding = looseBuilding;
        if (needMessage != null && !needMessage.isBlank()) {
            TicketStore.matchProfileNeedMessage = needMessage.trim();
        } else {
            TicketStore.matchProfileNeedMessage = "请先在个人资料填写楼栋与房间";
        }
        if (denyMessage != null && !denyMessage.isBlank()) {
            TicketStore.matchProfileDenyMessage = denyMessage.trim();
        } else {
            TicketStore.matchProfileDenyMessage = "只能对本寝室的查寝场次登记归寝";
        }
    
    }


    public static void configureBedConstraint(boolean enabled, String needMessage, String denyMessage) {
        TicketStore.bedConstraint = enabled;
        if (needMessage != null && !needMessage.isBlank()) {
            TicketStore.bedConstraintNeedMessage = needMessage.trim();
        }
        if (denyMessage != null && !denyMessage.isBlank()) {
            TicketStore.bedConstraintDenyMessage = denyMessage.trim();
        }
    
    }


    
    public static void configureApproveThicken(
            boolean approveThickenIn,
            boolean allowApproveCcIn,
            int minApproveRemarkWordsIn,
            boolean allowApproveTransferIn,
            boolean allowApproveDelegateIn,
            boolean allowApproveRemarkAttachIn,
            boolean allowApproveCcCommentIn,
            boolean allowApproveAutoPassIn,
            int approveAutoPassHoursIn) {
        TicketStore.approveThicken = approveThickenIn;
        TicketStore.allowApproveCc = allowApproveCcIn;
        TicketStore.minApproveRemarkWords = Math.max(0, Math.min(500, minApproveRemarkWordsIn));
        TicketStore.allowApproveTransfer = allowApproveTransferIn;
        TicketStore.allowApproveDelegate = allowApproveDelegateIn;
        TicketStore.allowApproveRemarkAttach = allowApproveRemarkAttachIn;
        TicketStore.allowApproveCcComment = allowApproveCcCommentIn;
        TicketStore.allowApproveAutoPass = allowApproveAutoPassIn;
        TicketStore.approveAutoPassHours = Math.max(0, Math.min(720, approveAutoPassHoursIn));
    }

    public static void configureApproveSkin(
            boolean allowCertPickupIn,
            boolean allowCertUrgentIn,
            boolean allowSealCopiesIn,
            boolean allowFleetMileageIn,
            boolean allowExpenseInvoiceIn,
            boolean allowVisitorCountIn) {
        TicketStore.allowCertPickup = allowCertPickupIn;
        TicketStore.allowCertUrgent = allowCertUrgentIn;
        TicketStore.allowSealCopies = allowSealCopiesIn;
        TicketStore.allowFleetMileage = allowFleetMileageIn;
        TicketStore.allowExpenseInvoice = allowExpenseInvoiceIn;
        TicketStore.allowVisitorCount = allowVisitorCountIn;
    }


    public static void configureApproveBatch4(
            boolean allowAwardCertNoIn,
            boolean allowVendorQuotesIn,
            boolean forceOnePerArchiveIn,
            int minVendorQuotesIn,
            int notifyArchiveExpireDaysIn,
            String onePerArchiveDenyMessageIn) {
        TicketStore.allowAwardCertNo = allowAwardCertNoIn;
        TicketStore.allowVendorQuotes = allowVendorQuotesIn;
        TicketStore.forceOnePerArchive = forceOnePerArchiveIn;
        TicketStore.minVendorQuotes = Math.max(0, Math.min(20, minVendorQuotesIn));
        TicketStore.notifyArchiveExpireDays = Math.max(0, Math.min(90, notifyArchiveExpireDaysIn));
        TicketStore.onePerArchiveDenyMessage =
                onePerArchiveDenyMessageIn == null ? "" : onePerArchiveDenyMessageIn.trim();
        if (TicketStore.forceOnePerArchive) {
            TicketStore.allowMultiTicket = false;
        }
    }

    public static void configureApproveBatch5(
            boolean allowEvalOpenWindowIn,
            boolean allowCompHoursIn,
            boolean allowFleetCrewIn,
            boolean allowEthicBatchIn,
            String evalOpenWindowDenyMessageIn) {
        TicketStore.allowEvalOpenWindow = allowEvalOpenWindowIn;
        TicketStore.allowCompHours = allowCompHoursIn;
        TicketStore.allowFleetCrew = allowFleetCrewIn;
        TicketStore.allowEthicBatch = allowEthicBatchIn;
        TicketStore.evalOpenWindowDenyMessage =
                evalOpenWindowDenyMessageIn == null ? "" : evalOpenWindowDenyMessageIn.trim();
    }

    public static void configureApproveBatch6(
            boolean allowPassExpireIn,
            boolean allowReturnFuelIn,
            boolean allowLaborPlaceIn,
            boolean allowPromoPlaceIn,
            boolean allowEthicMeetingIn,
            boolean allowEffectiveOnIn,
            int passExpireDaysIn) {
        TicketStore.allowPassExpire = allowPassExpireIn;
        TicketStore.allowReturnFuel = allowReturnFuelIn;
        TicketStore.allowLaborPlace = allowLaborPlaceIn;
        TicketStore.allowPromoPlace = allowPromoPlaceIn;
        TicketStore.allowEthicMeeting = allowEthicMeetingIn;
        TicketStore.allowEffectiveOn = allowEffectiveOnIn;
        TicketStore.passExpireDays = Math.max(0, Math.min(30, passExpireDaysIn));
    }

    public static void configureApproveBatch7(
            boolean allowCertIssueNoIn,
            boolean allowPromoFeedbackIn,
            boolean allowDocRevIn,
            boolean allowFitoutQuietIn) {
        TicketStore.allowCertIssueNo = allowCertIssueNoIn;
        TicketStore.allowPromoFeedback = allowPromoFeedbackIn;
        TicketStore.allowDocRev = allowDocRevIn;
        TicketStore.allowFitoutQuiet = allowFitoutQuietIn;
    }

    public static void configureApproveBatch8(
            boolean allowSealClosePhotoIn,
            boolean allowIssueCopiesIn,
            boolean allowSignPartiesIn,
            boolean allowTrainHoursIn,
            boolean allowInspectExpireIn,
            boolean allowMemberChangeIn) {
        TicketStore.allowSealClosePhoto = allowSealClosePhotoIn;
        TicketStore.allowIssueCopies = allowIssueCopiesIn;
        TicketStore.allowSignParties = allowSignPartiesIn;
        TicketStore.allowTrainHours = allowTrainHoursIn;
        TicketStore.allowInspectExpire = allowInspectExpireIn;
        TicketStore.allowMemberChange = allowMemberChangeIn;
    }

    public static void configureApproveBatch9(
            boolean allowProcureBudgetIn,
            boolean allowCheckinExceptionIn,
            boolean allowVisitPurposeIn,
            boolean allowFleetViolationIn,
            boolean allowFitoutRectifyIn,
            boolean allowProjNodeRemindIn) {
        TicketStore.allowProcureBudget = allowProcureBudgetIn;
        TicketStore.allowCheckinException = allowCheckinExceptionIn;
        TicketStore.allowVisitPurpose = allowVisitPurposeIn;
        TicketStore.allowFleetViolation = allowFleetViolationIn;
        TicketStore.allowFitoutRectify = allowFitoutRectifyIn;
        TicketStore.allowProjNodeRemind = allowProjNodeRemindIn;
    }

    public static void configureApproveBatch10(
            boolean allowClubCopyLastIn,
            boolean allowProcureReturnIn,
            boolean allowMoralObjectionIn,
            boolean allowProjFundUseIn,
            boolean allowEvalDimWeightIn,
            boolean allowVisitSlotRemainIn) {
        TicketStore.allowClubCopyLast = allowClubCopyLastIn;
        TicketStore.allowProcureReturn = allowProcureReturnIn;
        TicketStore.allowMoralObjection = allowMoralObjectionIn;
        TicketStore.allowProjFundUse = allowProjFundUseIn;
        TicketStore.allowEvalDimWeight = allowEvalDimWeightIn;
        TicketStore.allowVisitSlotRemain = allowVisitSlotRemainIn;
    }

    public static void configureApproveBatch11(
            boolean allowPlagiarismUrlIn,
            boolean allowAbsentStreakIn,
            boolean allowPartyStageIn,
            boolean allowEvalObserveIn,
            boolean allowScheduleImpactIn,
            boolean allowContractAmountIn) {
        TicketStore.allowPlagiarismUrl = allowPlagiarismUrlIn;
        TicketStore.allowAbsentStreak = allowAbsentStreakIn;
        TicketStore.allowPartyStage = allowPartyStageIn;
        TicketStore.allowEvalObserve = allowEvalObserveIn;
        TicketStore.allowScheduleImpact = allowScheduleImpactIn;
        TicketStore.allowContractAmount = allowContractAmountIn;
    }

    public static void configureApproveBatch12(
            boolean allowExpenseLinesIn,
            boolean allowTripLegsIn,
            boolean allowHideEvalResultIn,
            boolean allowSignRemarkVisibleIn,
            boolean allowProjChangeLogIn,
            boolean allowCertVerifyIn) {
        TicketStore.allowExpenseLines = allowExpenseLinesIn;
        TicketStore.allowTripLegs = allowTripLegsIn;
        TicketStore.allowHideEvalResult = allowHideEvalResultIn;
        TicketStore.allowSignRemarkVisible = allowSignRemarkVisibleIn;
        TicketStore.allowProjChangeLog = allowProjChangeLogIn;
        TicketStore.allowCertVerify = allowCertVerifyIn;
    }

    public static void configureApproveBatch13(
            boolean allowVisitWalkInIn,
            boolean allowCheckinProxyIn,
            boolean allowClubRosterIn,
            boolean allowCarpassParkingMutexIn,
            boolean allowEvalUrgeIn,
            boolean allowContractRenewIn) {
        TicketStore.allowVisitWalkIn = allowVisitWalkInIn;
        TicketStore.allowCheckinProxy = allowCheckinProxyIn;
        TicketStore.allowClubRoster = allowClubRosterIn;
        TicketStore.allowCarpassParkingMutex = allowCarpassParkingMutexIn;
        TicketStore.allowEvalUrge = allowEvalUrgeIn;
        TicketStore.allowContractRenew = allowContractRenewIn;
    }

    public static void configureApproveBatch14(
            boolean allowContractExpireRemindIn,
            boolean allowCertPickupRedeemIn,
            boolean allowExamPassMinIn,
            boolean allowCheckinSpotIn,
            boolean allowEvalBeforeGradeIn,
            boolean allowApproveDurationStatsIn) {
        TicketStore.allowContractExpireRemind = allowContractExpireRemindIn;
        TicketStore.allowCertPickupRedeem = allowCertPickupRedeemIn;
        TicketStore.allowExamPassMin = allowExamPassMinIn;
        TicketStore.allowCheckinSpot = allowCheckinSpotIn;
        TicketStore.allowEvalBeforeGrade = allowEvalBeforeGradeIn;
        TicketStore.allowApproveDurationStats = allowApproveDurationStatsIn;
    }

    public static void configureApproveBatch15(
            boolean allowAttachKeepOldIn,
            boolean allowCertPickupQrIn,
            boolean allowCertVerifyPageIn,
            boolean allowVisitorPassPrintIn,
            boolean allowCheckinDailyReportIn,
            boolean allowEvalCollegeExportIn) {
        TicketStore.allowAttachKeepOld = allowAttachKeepOldIn;
        TicketStore.allowCertPickupQr = allowCertPickupQrIn;
        TicketStore.allowCertVerifyPage = allowCertVerifyPageIn;
        TicketStore.allowVisitorPassPrint = allowVisitorPassPrintIn;
        TicketStore.allowCheckinDailyReport = allowCheckinDailyReportIn;
        TicketStore.allowEvalCollegeExport = allowEvalCollegeExportIn;
    }

    public static void configureApproveBatch16(
            boolean allowSealLedgerExportIn,
            boolean allowMoralMaterialCheckIn,
            boolean allowPartyMaterialTemplateIn,
            boolean allowPartyThoughtAttachIn) {
        TicketStore.allowSealLedgerExport = allowSealLedgerExportIn;
        TicketStore.allowMoralMaterialCheck = allowMoralMaterialCheckIn;
        TicketStore.allowPartyMaterialTemplate = allowPartyMaterialTemplateIn;
        TicketStore.allowPartyThoughtAttach = allowPartyThoughtAttachIn;
    }

    public static void configureApproveBatch17(
            boolean allowCertFormPrintIn,
            boolean allowSealFormPrintIn,
            boolean allowProjMidFormPrintIn,
            boolean allowEthicOpinionPrintIn,
            boolean allowExpenseAttachCountIn,
            boolean allowFleetDriverCertIn) {
        TicketStore.allowCertFormPrint = allowCertFormPrintIn;
        TicketStore.allowSealFormPrint = allowSealFormPrintIn;
        TicketStore.allowProjMidFormPrint = allowProjMidFormPrintIn;
        TicketStore.allowEthicOpinionPrint = allowEthicOpinionPrintIn;
        TicketStore.allowExpenseAttachCount = allowExpenseAttachCountIn;
        TicketStore.allowFleetDriverCert = allowFleetDriverCertIn;
    }


    public static void configureApplyThicken(
            boolean applyThickenIn,
            boolean notifyOnApplySuccessIn,
            boolean allowMeetingPlaceIn,
            boolean allowEmergencyContactIn,
            int cancelBeforeHoursIn,
            int claimCooldownHoursIn,
            int maxDropTimesIn,
            int semesterCreditCapIn,
            int creditWarnRemainingIn) {
        TicketStore.applyThicken = applyThickenIn;
        TicketStore.notifyOnApplySuccess = notifyOnApplySuccessIn;
        TicketStore.allowMeetingPlace = allowMeetingPlaceIn;
        TicketStore.allowEmergencyContact = allowEmergencyContactIn;
        TicketStore.cancelBeforeHours = Math.max(0, Math.min(720, cancelBeforeHoursIn));
        TicketStore.claimCooldownHours = Math.max(0, Math.min(168, claimCooldownHoursIn));
        TicketStore.maxDropTimes = Math.max(0, Math.min(30, maxDropTimesIn));
        TicketStore.semesterCreditCap = Math.max(0, Math.min(200, semesterCreditCapIn));
        TicketStore.creditWarnRemaining = Math.max(0, Math.min(50, creditWarnRemainingIn));
    
    }


    public static void configureFollowThicken(
            int followRemindDaysIn,
            int minRemarkWordsIn,
            int maxReviseTimesIn,
            boolean requireCloseAttachIn,
            boolean requireReturnDateIn,
            boolean requireFeedbackSetIn,
            boolean requireAppraisalIn,
            boolean allowDealAmountIn,
            boolean allowNextActionIn,
            boolean allowInterviewResultIn,
            boolean allowWrittenScoreIn,
            boolean allowBgCheckNoteIn,
            boolean allowDefenseResultIn,
            boolean maskBankAccountIn,
            boolean allowDisburseBatchIn,
            boolean allowLeaveProxyIn,
            boolean allowCompanyEvalIn,
            boolean allowExcellentMarkIn,
            boolean allowRecordUrlIn,
            boolean allowConfidentialIn,
            boolean allowAssignDeptIn,
            boolean allowBatchHireIn,
            boolean weekReportRemindIn,
            boolean homeVisitTemplateIn,
            boolean attachByLeaveTypeIn,
            boolean allowMakeupApplyIn,
            int weekReportDeadlineDayIn) {
        TicketStore.followRemindDays = Math.max(0, Math.min(14, followRemindDaysIn));
        TicketStore.minRemarkWords = Math.max(0, Math.min(5000, minRemarkWordsIn));
        TicketStore.maxReviseTimes = Math.max(0, Math.min(20, maxReviseTimesIn));
        TicketStore.requireCloseAttach = requireCloseAttachIn;
        TicketStore.requireReturnDate = requireReturnDateIn;
        TicketStore.requireFeedbackSet = requireFeedbackSetIn;
        TicketStore.requireAppraisal = requireAppraisalIn;
        TicketStore.allowDealAmount = allowDealAmountIn;
        TicketStore.allowNextAction = allowNextActionIn;
        TicketStore.allowInterviewResult = allowInterviewResultIn;
        TicketStore.allowWrittenScore = allowWrittenScoreIn;
        TicketStore.allowBgCheckNote = allowBgCheckNoteIn;
        TicketStore.allowDefenseResult = allowDefenseResultIn;
        TicketStore.maskBankAccount = maskBankAccountIn;
        TicketStore.allowDisburseBatch = allowDisburseBatchIn;
        TicketStore.allowLeaveProxy = allowLeaveProxyIn;
        TicketStore.allowCompanyEval = allowCompanyEvalIn;
        TicketStore.allowExcellentMark = allowExcellentMarkIn;
        TicketStore.allowRecordUrl = allowRecordUrlIn;
        TicketStore.allowConfidential = allowConfidentialIn;
        TicketStore.allowAssignDept = allowAssignDeptIn;
        TicketStore.allowBatchHire = allowBatchHireIn;
        TicketStore.weekReportRemind = weekReportRemindIn;
        TicketStore.homeVisitTemplate = homeVisitTemplateIn;
        TicketStore.attachByLeaveType = attachByLeaveTypeIn;
        TicketStore.allowMakeupApply = allowMakeupApplyIn;
        TicketStore.weekReportDeadlineDay = Math.max(0, Math.min(28, weekReportDeadlineDayIn));
    
    }

    /** 事件组闸：等级影响处理时限 + 上报群发值班。 */

    public static void configureEventOps(
            boolean levelSlaIn, int highDaysIn, int midDaysIn, int lowDaysIn, boolean dutyNotifyIn) {
        TicketStore.levelSla = levelSlaIn;
        TicketStore.levelSlaHighDays = Math.max(1, Math.min(60, highDaysIn));
        TicketStore.levelSlaMidDays = Math.max(1, Math.min(60, midDaysIn));
        TicketStore.levelSlaLowDays = Math.max(1, Math.min(60, lowDaysIn));
        TicketStore.dutyNotify = dutyNotifyIn;
    
    }


    public static void configureRepairThicken(
            boolean repairThickenIn,
            boolean allowUserUrgeIn,
            int urgeCooldownMinutesIn,
            boolean lockUrgeAfterRateIn,
            boolean allowCancelUrgeIn,
            boolean requireFaultReasonIn,
            boolean requireCloseSummaryIn,
            boolean requireLowRatingRemarkIn,
            boolean slaSplitIn,
            boolean escalateOnOverdueIn,
            boolean notifySupervisorOnOverdueIn,
            boolean allowHoldResumeIn,
            boolean allowCancelDispatchedIn,
            boolean allowTicketDraftIn,
            boolean allowFollowRateIn,
            boolean preferredSlotIn,
            boolean progressSubscribeIn,
            boolean nightUrgentIn,
            boolean allowPartsNoteIn,
            boolean allowQuoteIn,
            boolean allowPublicAreaIn,
            boolean dupRoomCheckIn,
            boolean allowAssetCodeIn,
            boolean allowRemoteUrlIn,
            boolean allowSerialNoIn,
            boolean allowHelperIn,
            boolean allowRatingTagsIn,
            boolean todayBoardIn,
            boolean printTicketIn) {
        TicketStore.repairThicken = repairThickenIn;
        TicketStore.allowUserUrge = allowUserUrgeIn;
        TicketStore.urgeCooldownMinutes = Math.max(0, Math.min(1440, urgeCooldownMinutesIn));
        TicketStore.lockUrgeAfterRate = lockUrgeAfterRateIn;
        TicketStore.allowCancelUrge = allowCancelUrgeIn;
        TicketStore.requireFaultReason = requireFaultReasonIn;
        TicketStore.requireCloseSummary = requireCloseSummaryIn;
        TicketStore.requireLowRatingRemark = requireLowRatingRemarkIn;
        TicketStore.slaSplit = slaSplitIn;
        TicketStore.escalateOnOverdue = escalateOnOverdueIn;
        TicketStore.notifySupervisorOnOverdue = notifySupervisorOnOverdueIn;
        TicketStore.allowHoldResume = allowHoldResumeIn;
        TicketStore.allowCancelDispatched = allowCancelDispatchedIn;
        TicketStore.allowTicketDraft = allowTicketDraftIn;
        TicketStore.allowFollowRate = allowFollowRateIn;
        TicketStore.preferredSlot = preferredSlotIn;
        TicketStore.progressSubscribe = progressSubscribeIn;
        TicketStore.nightUrgent = nightUrgentIn;
        TicketStore.allowPartsNote = allowPartsNoteIn;
        TicketStore.allowQuote = allowQuoteIn;
        TicketStore.allowPublicArea = allowPublicAreaIn;
        TicketStore.dupRoomCheck = dupRoomCheckIn;
        TicketStore.allowAssetCode = allowAssetCodeIn;
        TicketStore.allowRemoteUrl = allowRemoteUrlIn;
        TicketStore.allowSerialNo = allowSerialNoIn;
        TicketStore.allowHelper = allowHelperIn;
        TicketStore.allowRatingTags = allowRatingTagsIn;
        TicketStore.todayBoard = todayBoardIn;
        TicketStore.printTicket = printTicketIn;
    
    }

    /** 借期/在途上限/逾期费/默认领取地（≤0 或空表示保持默认） */

    public static void configureBizParams(int loanDays, int maxActive, double finePerDay, String pickupPlace) {
        if (loanDays > 0) TicketStore.bizLoanDays = Math.min(365, loanDays);
        if (maxActive > 0) TicketStore.bizMaxActive = Math.min(200, maxActive);
        if (finePerDay >= 0) TicketStore.bizFinePerDay = Math.min(100.0, finePerDay);
        if (pickupPlace != null && !pickupPlace.isBlank()) TicketStore.bizPickupPlace = pickupPlace.trim();
    
    }


    public static void configureRenew(boolean enabled, int maxTimes, int days) {
        TicketStore.allowRenew = enabled;
        TicketStore.maxRenew = Math.max(1, Math.min(5, maxTimes <= 0 ? 1 : maxTimes));
        TicketStore.renewDays = Math.max(0, days);
        if (TicketStore.allowRenew) {
            TicketStore.ensureColumn("renew_count", "INT NOT NULL DEFAULT 0");
        }
    
    }


    public static void configureDueSoon(int days) {
        TicketStore.dueSoonDays = Math.max(0, Math.min(14, days));
        if (TicketStore.dueSoonDays > 0) {
            TicketStore.ensureColumn("due_soon_notified_at", "DATETIME NULL");
        }
    
    }


    public static void configureMaxOverdueTimes(int times) {
        TicketStore.maxOverdueTimes = Math.max(0, Math.min(20, times));
        if (TicketStore.maxOverdueTimes > 0) {
            TicketStore.ensureColumn("ever_overdue", "TINYINT NOT NULL DEFAULT 0");
        }
    
    }


    public static void configureBookHold(boolean enabled, int hours) {
        TicketStore.allowBookHold = enabled;
        TicketStore.holdHours = Math.max(1, Math.min(168, hours <= 0 ? 48 : hours));
        if (TicketStore.allowBookHold) {
            TicketStore.ensureColumn("hold_expire_at", "DATETIME NULL");
        }
    
    }


    public static void configureRequireReturnAttach(boolean enabled) {
        TicketStore.requireReturnAttach = enabled;
        if (TicketStore.requireReturnAttach) {
            TicketStore.ensureColumn("attach_url", "VARCHAR(255) DEFAULT ''");
        }
    
    }
    public static void configureRequireClaimProof(boolean enabled) {
        TicketStore.requireClaimProof = enabled;
    }

    public static void configureApplicantCompleteOnly(boolean enabled) {
        TicketStore.applicantCompleteOnly = enabled;
    }

    public static void configureLoanOptions(boolean pickPeriod, boolean qtyEnabled) {
        TicketStore.pickLoanPeriod = pickPeriod && TicketStore.useDeadline;
        TicketStore.allowQty = qtyEnabled && TicketStore.MODE == TicketStore.Mode.ARCHIVE
                && (TicketStore.useQuota || TicketStore.timebankRedeem);
    }

    public static void configureApplyExtras(boolean remarkRequired, boolean dateRange) {
        TicketStore.requireRemark = remarkRequired;
        TicketStore.pickDateRange = dateRange && TicketStore.MODE == TicketStore.Mode.ARCHIVE;
    }

    public static void configureApproveEndsFlow(boolean enabled) {
        TicketStore.approveEndsFlow = enabled;
    }

    public static void configureAutoApprove(boolean enabled) {
        TicketStore.autoApprove = enabled;
    }

    public static void configureRequireClaimCode(boolean enabled) {
        TicketStore.requireClaimCode = enabled;
    }

    public static void configureProxyPickup(boolean enabled) {
        TicketStore.allowProxyPickup = enabled;
    }

    public static void configureArrivalNotify(boolean enabled) {
        TicketStore.arrivalNotify = enabled;
    }

    public static void configureNoticeAck(boolean enabled) {
        TicketStore.requireNoticeAck = enabled;
    }

    public static void configureDeposit(boolean enabled) {
        TicketStore.allowDeposit = enabled;
    }

    public static void configureExceptionClose(boolean enabled) {
        TicketStore.allowExceptionClose = enabled;
    }

    public static void configureTrainingAck(boolean enabled) {
        TicketStore.requireTrainingAck = enabled;
    }

    public static void configureInsuranceAck(boolean enabled) {
        TicketStore.requireInsuranceAck = enabled;
    }

    public static void configureMeetingAck(boolean enabled) {
        TicketStore.requireMeetingAck = enabled;
    }

    public static void configureApplyInvite(boolean enabled) {
        TicketStore.requireApplyInvite = enabled;
    }

    public static void configurePriceNoteAck(boolean enabled) {
        TicketStore.requirePriceNoteAck = enabled;
    }

    public static void configureSponsorAck(boolean enabled) {
        TicketStore.requireSponsorAck = enabled;
    }

    public static void configurePlanAck(boolean enabled) {
        TicketStore.requirePlanAck = enabled;
    }

    public static void configurePrereqAck(boolean enabled) {
        TicketStore.requirePrereqAck = enabled;
    }

    public static void configureAgeConstraint(boolean enabled, String needMessage, String denyMessage) {
        TicketStore.ageConstraint = enabled;
        if (needMessage != null && !needMessage.isBlank()) {
            TicketStore.ageConstraintNeedMessage = needMessage.trim();
        }
        if (denyMessage != null && !denyMessage.isBlank()) {
            TicketStore.ageConstraintDenyMessage = denyMessage.trim();
        }
    }

    public static void configureLateMinutes(boolean enabled) {
        TicketStore.allowLateMinutes = enabled;
    }

    public static void configureWishOrder(boolean enabled) {
        TicketStore.allowWishOrder = enabled;
    }

    public static void configureVolunteerRole(boolean enabled) {
        TicketStore.allowVolunteerRole = enabled;
    }

    public static void configureAdminCheckin(boolean enabled) {
        TicketStore.allowAdminCheckin = enabled;
    }

    public static void configureTourNoticeAck(boolean enabled) {
        TicketStore.requireTourNoticeAck = enabled;
    }

    public static void configureCompanions(boolean enabled) {
        TicketStore.allowCompanions = enabled;
    }

    public static void configureLottery(boolean enabled) {
        TicketStore.allowLottery = enabled;
    }

    public static void configureSeatZone(boolean enabled) {
        TicketStore.allowSeatZone = enabled;
    }

    public static void configureTicketTransfer(boolean enabled) {
        TicketStore.allowTicketTransfer = enabled;
    }

    public static void configureTicketWallet(boolean enabled) {
        TicketStore.allowTicketWallet = enabled;
    }

    public static void configureApplyBlacklist(boolean enabled) {
        TicketStore.allowApplyBlacklist = enabled;
    }

    public static void configureScheduleChangeNotify(boolean enabled) {
        TicketStore.scheduleChangeNotify = enabled;
    }

    public static void configurePostGallery(boolean enabled) {
        TicketStore.allowPostGallery = enabled;
    }

    public static void configureCreditWritebackAck(boolean enabled) {
        TicketStore.requireCreditWritebackAck = enabled;
    }

    public static void configureCalibBlock(boolean enabled) {
        TicketStore.blockIfCalibExpired = enabled;
    }

    public static void configureProjectNo(boolean enabled) {
        TicketStore.allowProjectNo = enabled;
    }

    public static void configureProcureRef(boolean enabled) {
        TicketStore.allowProcureRef = enabled;
    }

    public static void configureProcureToStockIn(boolean enabled) {
        TicketStore.procureToStockIn = enabled;
    }

    public static void configureDualReview(boolean enabled) {
        TicketStore.allowDualReview = enabled;
    }

    public static void configureShipFee(boolean enabled) {
        TicketStore.allowShipFee = enabled;
    }

    public static void configureUtilityNote(boolean enabled) {
        TicketStore.allowUtilityNote = enabled;
    }

    public static void configureMaxCancelHolds(int max) {
        TicketStore.maxCancelHolds = Math.max(0, Math.min(20, max));
    }

    public static void configureOverdueAutoCompensate(boolean enabled) {
        TicketStore.overdueAutoCompensate = enabled;
    }

    public static void configureFineWaive(boolean enabled) {
        TicketStore.allowFineWaive = enabled;
    }

    public static void configureRenewBlockIfHeld(boolean enabled) {
        TicketStore.renewBlockIfHeld = enabled;
    }

    public static void configurePeerConfirm(boolean enabled) {
        TicketStore.requirePeerConfirm = enabled;
    }

    public static void configureAbandonDual(boolean enabled) {
        TicketStore.requireAbandonDual = enabled;
    }

    public static void configureFollowOps(int staleFollowDaysIn, boolean phoneDupCheckIn) {
        TicketStore.staleFollowDays = Math.max(0, Math.min(90, staleFollowDaysIn));
        TicketStore.phoneDupCheck = phoneDupCheckIn;
    }

    public static void configureRules(boolean mutex, int catLimit) {
        TicketStore.checkMutex = mutex;
        TicketStore.categoryLimit = Math.max(0, catLimit);
    }

    public static void configureCheckin(boolean enabled) {
        TicketStore.allowCheckin = enabled;
    }

    public static void configurePeerAccept(boolean enabled) {
        TicketStore.peerAccept = enabled;
    }

    public static void configureIssuePassCode(boolean enabled) {
        TicketStore.issuePassCode = enabled;
    }

    public static void configureWaitlist(boolean enabled) {
        TicketStore.allowWaitlist = enabled;
    }

    public static void configureBookLost(boolean enabled) {
        TicketStore.allowBookLost = enabled;
    }

    public static void configureNoShow(boolean afterEnd, double penaltyYuan) {
        TicketStore.noShowAfterEnd = afterEnd && TicketStore.allowCheckin;
        TicketStore.noShowPenaltyYuan = Math.max(0, penaltyYuan);
    }
}
