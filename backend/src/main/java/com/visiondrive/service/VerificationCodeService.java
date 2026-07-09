package com.visiondrive.service;

import com.visiondrive.service.sms.SmsSender;
import com.visiondrive.util.VerificationCodeStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.util.concurrent.ThreadLocalRandom;

@Slf4j
@Service
@RequiredArgsConstructor
public class VerificationCodeService {

    private final VerificationCodeStore store;
    private final SmsSender smsSender;

    @Value("${sms.provider:mock}")
    private String smsProvider;

    public SendResult sendCode(String phone) {
        if (phone == null || !phone.matches("^1[3-9]\\d{9}$")) return SendResult.fail("手机号格式不正确");
        String code = String.format("%06d", ThreadLocalRandom.current().nextInt(1000000));
        Long blocked = store.saveCode(phone, code);
        if (blocked != null) {
            return blocked == -1 ? SendResult.fail("今日发送次数已达上限") : SendResult.retryAfter(blocked);
        }
        if (!smsSender.send(phone, code)) return SendResult.fail("验证码发送失败");
        log.info("验证码已发送: phone={}", phone.substring(0, 3) + "****");
        return "mock".equals(smsProvider) ? SendResult.okWithMockCode(code) : SendResult.ok();
    }

    public String verifyCode(String phone, String code) {
        return store.verifyCode(phone, code);
    }

    public static class SendResult {
        public boolean success;
        public String message;
        public Long retryAfter;
        public String mockCode;
        public static SendResult ok() { SendResult r = new SendResult(); r.success = true; r.message = "验证码已发送"; return r; }
        public static SendResult okWithMockCode(String code) { SendResult r = ok(); r.mockCode = code; return r; }
        public static SendResult fail(String msg) { SendResult r = new SendResult(); r.success = false; r.message = msg; return r; }
        public static SendResult retryAfter(long s) { SendResult r = new SendResult(); r.success = false; r.message = "请 " + s + " 秒后再试"; r.retryAfter = s; return r; }
    }
}
