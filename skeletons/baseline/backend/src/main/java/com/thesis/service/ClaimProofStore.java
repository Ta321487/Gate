package com.thesis.service;

import com.thesis.capability.TicketStore;
import com.thesis.config.JdbcSupport;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 失物认领凭证：提交 → verifying → 核验通过后才可审批。
 */
public class ClaimProofStore {

    private static final Set<String> PROOF_TYPES = Set.of("photo", "desc", "receipt");

    private static boolean enabled;
    private static Boolean tableReady;

    private ClaimProofStore() {}

    public static void configure(boolean on) {
        enabled = on;
        tableReady = null;
        TicketStore.configureRequireClaimProof(on);
    }

    public static boolean enabled() {
        return enabled;
    }

    private static JdbcTemplate db() {
        return JdbcSupport.jdbc();
    }

    public static boolean ready() {
        if (!enabled) return false;
        if (tableReady != null) return tableReady;
        try {
            Integer n = db().queryForObject(
                    "SELECT COUNT(*) FROM information_schema.tables "
                            + "WHERE table_schema=DATABASE() AND table_name='lost_claim_proof'",
                    Integer.class);
            tableReady = n != null && n > 0;
        } catch (Exception e) {
            tableReady = false;
        }
        return tableReady;
    }

    private static void require() {
        if (!ready()) throw new IllegalStateException("认领凭证功能暂不可用");
    }

    private static Map<String, Object> mapRow(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("claimId", rs.getLong("claim_id"));
        m.put("proofType", rs.getString("proof_type"));
        m.put("proofContent", rs.getString("proof_content"));
        m.put("verifyStatus", rs.getString("verify_status"));
        m.put("verifierId", rs.getString("verifier_id"));
        m.put("createdAt", rs.getTimestamp("created_at") == null
                ? null : rs.getTimestamp("created_at").toLocalDateTime().toString().replace('T', ' '));
        return m;
    }

    public static List<Map<String, Object>> listByClaim(long claimId) {
        require();
        return db().query(
                "SELECT * FROM lost_claim_proof WHERE claim_id=? ORDER BY id DESC",
                (rs, i) -> mapRow(rs),
                claimId);
    }

    public static boolean hasPassed(long claimId) {
        if (!enabled || !ready() || claimId <= 0) return false;
        Integer n = db().queryForObject(
                "SELECT COUNT(*) FROM lost_claim_proof WHERE claim_id=? AND verify_status='passed'",
                Integer.class,
                claimId);
        return n != null && n > 0;
    }

    /** 审批前：须已核验通过，否则硬拒绝（防点一下办结）。 */
    public static void assertPassed(long claimId) {
        if (!enabled || !ready()) return;
        if (!hasPassed(claimId)) {
            throw new IllegalStateException("认领凭证尚未核验通过，不能审批");
        }
    }

    public static long submit(long claimId, String proofType, String proofContent, String username) {
        require();
        if (claimId <= 0) throw new IllegalArgumentException("认领单无效");
        Map<String, Object> ticket = TicketStore.get(claimId);
        if (ticket == null) throw new IllegalArgumentException("认领单不存在");
        String owner = ticket.get("username") == null ? "" : String.valueOf(ticket.get("username"));
        String me = username == null ? "" : username.trim();
        if (!me.isBlank() && !me.equals(owner)) {
            throw new IllegalStateException("只能为自己的认领单提交凭证");
        }
        String st = String.valueOf(ticket.get("status"));
        if (!"pending".equals(st) && !"verifying".equals(st)) {
            throw new IllegalStateException("当前状态不可提交凭证");
        }
        String type = proofType == null ? "" : proofType.trim().toLowerCase();
        if ("照片".equals(proofType) || "photo".equals(type)) type = "photo";
        else if ("描述".equals(proofType) || "desc".equals(type) || "description".equals(type)) type = "desc";
        else if ("购买凭证".equals(proofType) || "receipt".equals(type)) type = "receipt";
        if (!PROOF_TYPES.contains(type)) {
            throw new IllegalArgumentException("凭证类型须为照片/描述/购买凭证");
        }
        String content = proofContent == null ? "" : proofContent.trim();
        if (content.isBlank()) throw new IllegalArgumentException("请填写凭证内容");
        if (content.length() > 500) content = content.substring(0, 500);

        String finalType = type;
        String finalContent = content;
        KeyHolder keys = new GeneratedKeyHolder();
        db().update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    "INSERT INTO lost_claim_proof (claim_id, proof_type, proof_content, verify_status) VALUES (?,?,?,'pending')",
                    Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, claimId);
            ps.setString(2, finalType);
            ps.setString(3, finalContent);
            return ps;
        }, keys);
        Number key = keys.getKey();
        long id = key == null ? 0L : key.longValue();
        TicketStore.markVerifying(claimId, me);
        return id;
    }

    public static Map<String, Object> verify(long proofId, boolean pass, String verifierId) {
        require();
        if (proofId <= 0) throw new IllegalArgumentException("凭证无效");
        List<Map<String, Object>> rows = db().query(
                "SELECT * FROM lost_claim_proof WHERE id=?",
                (rs, i) -> mapRow(rs),
                proofId);
        if (rows.isEmpty()) throw new IllegalArgumentException("凭证不存在");
        Map<String, Object> row = rows.get(0);
        if (!"pending".equals(String.valueOf(row.get("verifyStatus")))) {
            throw new IllegalStateException("该凭证已核验");
        }
        String vid = verifierId == null ? "" : verifierId.trim();
        String status = pass ? "passed" : "rejected";
        db().update(
                "UPDATE lost_claim_proof SET verify_status=?, verifier_id=? WHERE id=?",
                status, vid.isBlank() ? null : vid, proofId);
        if (!pass) {
            long claimId = ((Number) row.get("claimId")).longValue();
            // 驳回凭证后回到待交凭证，便于重交
            TicketStore.markPendingForProof(claimId, vid);
        }
        return listByClaim(((Number) row.get("claimId")).longValue()).stream()
                .filter(m -> proofId == ((Number) m.get("id")).longValue())
                .findFirst()
                .orElse(row);
    }
}
