package com.visiondrive.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 验证码内存存储，支持 TTL 过期 + 错误次数限制 + 频率限制
 */
@Slf4j
@Component
public class VerificationCodeStore {

    /** 验证码有效期（秒） */
    private static final long CODE_TTL_SECONDS = 300;
    /** 最大错误尝试次数 */
    private static final int MAX_ATTEMPTS = 5;
    /** 发送间隔（秒） */
    private static final long RESEND_INTERVAL_SECONDS = 60;
    /** 每日上限 */
    private static final int DAILY_LIMIT = 10;

    private final ConcurrentHashMap<String, CodeEntry> codeMap = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, DailyCounter> dailyCounterMap = new ConcurrentHashMap<>();

    /**
     * 保存验证码
     * @return 保存成功返回 null，频率限制返回重试秒数
     */
    public Long saveCode(String phone, String code) {
        String key = "code:" + phone;

        // 检查发送间隔
        CodeEntry existing = codeMap.get(key);
        if (existing != null) {
            long elapsed = Instant.now().getEpochSecond() - existing.createdAt;
            if (elapsed < RESEND_INTERVAL_SECONDS) {
                return RESEND_INTERVAL_SECONDS - elapsed;
            }
        }

        // 检查每日上限
        if (!canSendToday(phone)) {
            return -1L; // -1 表示达到每日上限
        }

        // 保存验证码
        codeMap.put(key, new CodeEntry(code, Instant.now().getEpochSecond()));
        incrementDailyCount(phone);
        log.info("[验证码] 手机号 {} 验证码: {} (有效 {} 秒)", maskPhone(phone), code, CODE_TTL_SECONDS);
        return null;
    }

    /**
     * 校验验证码
     * @return null=成功，否则返回错误消息
     */
    public String verifyCode(String phone, String code) {
        String key = "code:" + phone;
        CodeEntry entry = codeMap.get(key);

        if (entry == null) {
            return "验证码已过期或未发送，请重新获取";
        }

        // 检查过期
        long elapsed = Instant.now().getEpochSecond() - entry.createdAt;
        if (elapsed > CODE_TTL_SECONDS) {
            codeMap.remove(key);
            return "验证码已过期，请重新获取";
        }

        // 检查错误次数
        if (entry.attempts >= MAX_ATTEMPTS) {
            codeMap.remove(key);
            return "验证码错误次数过多，请重新获取";
        }

        // 比对验证码
        if (!entry.code.equals(code)) {
            entry.attempts++;
            int remaining = MAX_ATTEMPTS - entry.attempts;
            if (remaining <= 0) {
                codeMap.remove(key);
                return "验证码错误，已超过最大尝试次数，请重新获取";
            }
            return "验证码错误，还剩 " + remaining + " 次机会";
        }

        // 验证成功，删除验证码（一次性使用）
        codeMap.remove(key);
        return null;
    }

    private boolean canSendToday(String phone) {
        String today = java.time.LocalDate.now().toString();
        String key = today + ":" + phone;
        DailyCounter counter = dailyCounterMap.get(key);
        return counter == null || counter.count < DAILY_LIMIT;
    }

    private void incrementDailyCount(String phone) {
        String today = java.time.LocalDate.now().toString();
        String key = today + ":" + phone;
        dailyCounterMap.compute(key, (k, v) -> {
            if (v == null) return new DailyCounter(1);
            v.count++;
            return v;
        });
    }

    private String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) return "***";
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    /**
     * 定时清理过期验证码（每分钟）
     */
    @Scheduled(fixedDelay = 60000)
    public void cleanupExpired() {
        long now = Instant.now().getEpochSecond();
        codeMap.entrySet().removeIf(e -> now - e.getValue().createdAt > CODE_TTL_SECONDS);
        // 清理昨天的日计数器
        String yesterday = java.time.LocalDate.now().minusDays(1).toString();
        dailyCounterMap.keySet().removeIf(k -> k.startsWith(yesterday));
    }

    // --- 内部类 ---

    private static class CodeEntry {
        final String code;
        final long createdAt;
        int attempts;

        CodeEntry(String code, long createdAt) {
            this.code = code;
            this.createdAt = createdAt;
            this.attempts = 0;
        }
    }

    private static class DailyCounter {
        int count;
        DailyCounter(int count) { this.count = count; }
    }
}
