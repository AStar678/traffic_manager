package com.visiondrive.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class VerificationCodeStore {

    private static final long CODE_TTL_SECONDS = 300;
    private static final int MAX_ATTEMPTS = 5;
    private static final long RESEND_INTERVAL_SECONDS = 60;
    private static final int DAILY_LIMIT = 10;

    private final ConcurrentHashMap<String, CodeEntry> codeMap = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, DailyCounter> dailyCounterMap = new ConcurrentHashMap<>();

    public Long saveCode(String phone, String code) {
        String key = "code:" + phone;
        CodeEntry existing = codeMap.get(key);
        if (existing != null) {
            long elapsed = Instant.now().getEpochSecond() - existing.createdAt;
            if (elapsed < RESEND_INTERVAL_SECONDS) return RESEND_INTERVAL_SECONDS - elapsed;
        }
        if (!canSendToday(phone)) return -1L;
        codeMap.put(key, new CodeEntry(code, Instant.now().getEpochSecond()));
        incrementDailyCount(phone);
        log.info("[验证码] {} 验证码: {}", mask(phone), code);
        return null;
    }

    public String verifyCode(String phone, String code) {
        String key = "code:" + phone;
        CodeEntry entry = codeMap.get(key);
        if (entry == null) return "验证码已过期或未发送，请重新获取";
        long elapsed = Instant.now().getEpochSecond() - entry.createdAt;
        if (elapsed > CODE_TTL_SECONDS) { codeMap.remove(key); return "验证码已过期，请重新获取"; }
        if (entry.attempts >= MAX_ATTEMPTS) { codeMap.remove(key); return "验证码错误次数过多，请重新获取"; }
        if (!entry.code.equals(code)) {
            entry.attempts++;
            int remaining = MAX_ATTEMPTS - entry.attempts;
            if (remaining <= 0) { codeMap.remove(key); return "验证码错误，已超过最大尝试次数"; }
            return "验证码错误，还剩 " + remaining + " 次机会";
        }
        codeMap.remove(key);
        return null;
    }

    private boolean canSendToday(String phone) {
        String key = java.time.LocalDate.now() + ":" + phone;
        DailyCounter c = dailyCounterMap.get(key);
        return c == null || c.count < DAILY_LIMIT;
    }

    private void incrementDailyCount(String phone) {
        String key = java.time.LocalDate.now() + ":" + phone;
        dailyCounterMap.compute(key, (k, v) -> v == null ? new DailyCounter(1) : new DailyCounter(v.count + 1));
    }

    private String mask(String phone) {
        return phone == null || phone.length() < 7 ? "***" : phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    @Scheduled(fixedDelay = 60000)
    public void cleanup() {
        long now = Instant.now().getEpochSecond();
        codeMap.entrySet().removeIf(e -> now - e.getValue().createdAt > CODE_TTL_SECONDS);
        String yesterday = java.time.LocalDate.now().minusDays(1).toString();
        dailyCounterMap.keySet().removeIf(k -> k.startsWith(yesterday));
    }

    private static class CodeEntry { final String code; final long createdAt; int attempts; CodeEntry(String c, long t) { this.code = c; this.createdAt = t; }}
    private static class DailyCounter { int count; DailyCounter(int c) { this.count = c; }}
}
