package com.thesis.capability;

import com.thesis.config.DomainResourceJson;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class TicketCopy {

    static Map<String, String> STATE_LABELS = Map.of();
    static Map<String, String> VERB_LABELS = Map.of();
    static String CHECKIN_LABEL = "签到";
    static String FINE_PAID_LABEL = "费用已结清";
    static String ARCHIVE_LABEL = "";
    static String APPLY_DEADLINE_LABEL = "报名截止";
    /** bake 写入；空则运行时按动词兜底 */
    static String SIBLING_REJECT_TIP = "";
    /** C-06：维度 key → 显示名；空 = 单分评分 */
    static List<Map<String, String>> RATING_DIMS = List.of();
    static boolean ALLOW_ANONYMOUS_RATING = false;

    private TicketCopy() {}

    /** 读取 bake 写入的 domain-ticket-copy.json（states/verbs 文案）。 */
    static void loadCopyFromResource() {
        Map<String, Object> root = DomainResourceJson.loadObjectMap("domain-ticket-copy.json");
        if (root.isEmpty()) return;
        Object st = root.get("states");
        if (st instanceof Map<?, ?> map) {
            Map<String, String> out = stringMap(map);
            if (!out.isEmpty()) STATE_LABELS = out;
        }
        Object vb = root.get("verbs");
        if (vb instanceof Map<?, ?> map) {
            Map<String, String> out = stringMap(map);
            if (!out.isEmpty()) VERB_LABELS = out;
        }
        String cin = DomainResourceJson.str(root, "checkinLabel", "").trim();
        if (!cin.isBlank()) CHECKIN_LABEL = cin;
        String fp = DomainResourceJson.str(root, "finePaidLabel", "").trim();
        if (!fp.isBlank()) FINE_PAID_LABEL = fp;
        String arch = DomainResourceJson.str(root, "archiveLabel", "").trim();
        if (!arch.isBlank()) ARCHIVE_LABEL = arch;
        String dl = DomainResourceJson.str(root, "applyDeadlineLabel", "").trim();
        if (!dl.isBlank()) APPLY_DEADLINE_LABEL = dl;
        String sl = DomainResourceJson.str(root, "stockLabel", "").trim();
        if (!sl.isBlank()) ArchiveStore.configureStockLabel(sl);
        String srt = DomainResourceJson.str(root, "siblingRejectTip", "").trim();
        if (!srt.isBlank()) SIBLING_REJECT_TIP = srt;
        ALLOW_ANONYMOUS_RATING = Boolean.TRUE.equals(root.get("allowAnonymousRating"))
                || "true".equalsIgnoreCase(String.valueOf(root.get("allowAnonymousRating")));
        Object rd = root.get("ratingDims");
        if (rd instanceof List<?> list) {
            List<Map<String, String>> dims = new ArrayList<>();
            for (Object item : list) {
                if (!(item instanceof Map<?, ?> m)) continue;
                String key = String.valueOf(m.get("key") == null ? "" : m.get("key")).trim();
                String lab = String.valueOf(m.get("label") == null ? "" : m.get("label")).trim();
                if (key.isBlank() || lab.isBlank()) continue;
                Map<String, String> row = new LinkedHashMap<>();
                row.put("key", key);
                row.put("label", lab);
                dims.add(row);
            }
            RATING_DIMS = dims;
        }
    }

    private static Map<String, String> stringMap(Map<?, ?> map) {
        Map<String, String> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : map.entrySet()) {
            if (e.getKey() == null || e.getValue() == null) continue;
            String lab = String.valueOf(e.getValue()).trim();
            if (!lab.isBlank()) out.put(String.valueOf(e.getKey()), lab);
        }
        return out;
    }

    static String stateLabel(String key, String fallback) {
        if (key == null || key.isBlank()) return fallback;
        String lab = STATE_LABELS.get(key);
        return lab == null || lab.isBlank() ? fallback : lab;
    }

    static String verbLabel(String key, String fallback) {
        if (key == null || key.isBlank()) return fallback;
        String lab = VERB_LABELS.get(key);
        return lab == null || lab.isBlank() ? fallback : lab;
    }

    static String archiveNoun() {
        return ARCHIVE_LABEL.isBlank() ? "项目" : ARCHIVE_LABEL;
    }

    /** 库存扣尽自动驳回文案；无 bake 配置时按申请动词兜底（与 bake/ticket_copy_text 同源规则）。 */
    static String siblingRejectTip() {
        if (!SIBLING_REJECT_TIP.isBlank()) return SIBLING_REJECT_TIP;
        return fallbackSiblingRejectTip(archiveNoun(), verbLabel("apply", "申请"));
    }

    static String fallbackSiblingRejectTip(String noun, String applyVerb) {
        String n = noun == null || noun.isBlank() ? "项目" : noun;
        String v = applyVerb == null ? "" : applyVerb;
        String tip;
        if (v.contains("认领")) tip = "已确认认领";
        else if (v.contains("借阅") || v.contains("借用")) tip = "已借完";
        else if (v.contains("申领")) tip = "已申领完毕";
        else if (v.contains("选课") || v.contains("报名")) tip = "名额已满";
        else tip = "已无法再申请";
        return "「" + n + "」" + tip + "，系统自动驳回";
    }
}
