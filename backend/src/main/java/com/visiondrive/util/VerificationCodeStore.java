package com.visiondrive.util;

import com.visiondrive.model.dto.VerificationCodePurpose;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.LocalDate;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 进程内验证码存储。适合单实例实训环境；多实例部署时应替换为 Redis。
 */
@Component
public class VerificationCodeStore {

    static final long CODE_TTL_SECONDS = 300;
    static final long RESEND_INTERVAL_SECONDS = 60;
    static final int MAX_ATTEMPTS = 5;
    static final int DAILY_LIMIT = 10;

    private final ConcurrentHashMap<CodeKey, CodeEntry> codes = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> lastSentAt = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Integer> dailyCounts = new ConcurrentHashMap<>();

    public synchronized SaveResult saveCode(String phone, VerificationCodePurpose purpose, String code) {
        long now = Instant.now().getEpochSecond();
        Long previousSentAt = lastSentAt.get(phone);
        if (previousSentAt != null) {
            long retryAfter = RESEND_INTERVAL_SECONDS - (now - previousSentAt);
            if (retryAfter > 0) {
                return SaveResult.retryAfter(retryAfter);
            }
        }

        String counterKey = counterKey(phone);
        int count = dailyCounts.getOrDefault(counterKey, 0);
        if (count >= DAILY_LIMIT) {
            return SaveResult.limitReached();
        }

        codes.put(new CodeKey(phone, purpose), new CodeEntry(code, now));
        lastSentAt.put(phone, now);
        dailyCounts.put(counterKey, count + 1);
        return SaveResult.accepted();
    }

    public synchronized void rollbackCode(String phone, VerificationCodePurpose purpose, String code) {
        CodeKey codeKey = new CodeKey(phone, purpose);
        CodeEntry current = codes.get(codeKey);
        if (current == null || !current.code.equals(code)) {
            return;
        }
        codes.remove(codeKey);
        lastSentAt.computeIfPresent(phone, (key, sentAt) -> sentAt == current.createdAt ? null : sentAt);
        String counterKey = counterKey(phone);
        dailyCounts.computeIfPresent(counterKey, (key, count) -> count <= 1 ? null : count - 1);
    }

    /** @return null 表示校验成功，否则返回可展示的错误信息。 */
    public synchronized String verifyCode(String phone, VerificationCodePurpose purpose, String code) {
        CodeKey codeKey = new CodeKey(phone, purpose);
        CodeEntry entry = codes.get(codeKey);
        if (entry == null) {
            return "验证码已过期或未发送，请重新获取";
        }

        long elapsed = Instant.now().getEpochSecond() - entry.createdAt;
        if (elapsed > CODE_TTL_SECONDS) {
            codes.remove(codeKey);
            return "验证码已过期，请重新获取";
        }

        if (entry.attempts >= MAX_ATTEMPTS) {
            codes.remove(codeKey);
            return "验证码错误次数过多，请重新获取";
        }

        if (!entry.code.equals(code)) {
            entry.attempts++;
            int remaining = MAX_ATTEMPTS - entry.attempts;
            if (remaining <= 0) {
                codes.remove(codeKey);
                return "验证码错误，已超过最大尝试次数，请重新获取";
            }
            return "验证码错误，还剩 " + remaining + " 次机会";
        }

        codes.remove(codeKey);
        return null;
    }

    @Scheduled(fixedDelay = 60_000)
    public synchronized void cleanupExpired() {
        long now = Instant.now().getEpochSecond();
        codes.entrySet().removeIf(entry -> now - entry.getValue().createdAt > CODE_TTL_SECONDS);
        lastSentAt.entrySet().removeIf(entry -> now - entry.getValue() >= RESEND_INTERVAL_SECONDS);
        String todayPrefix = LocalDate.now() + ":";
        dailyCounts.keySet().removeIf(key -> !key.startsWith(todayPrefix));
    }

    private String counterKey(String phone) {
        return LocalDate.now() + ":" + phone;
    }

    private static final class CodeEntry {
        private final String code;
        private final long createdAt;
        private int attempts;

        private CodeEntry(String code, long createdAt) {
            this.code = code;
            this.createdAt = createdAt;
        }
    }

    private record CodeKey(String phone, VerificationCodePurpose purpose) {
    }

    public record SaveResult(boolean saved, Long retryAfter, boolean dailyLimitReached) {
        public static SaveResult accepted() {
            return new SaveResult(true, null, false);
        }

        public static SaveResult retryAfter(long seconds) {
            return new SaveResult(false, seconds, false);
        }

        public static SaveResult limitReached() {
            return new SaveResult(false, null, true);
        }
    }
}
