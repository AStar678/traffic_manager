package com.visiondrive.service;

import com.visiondrive.service.sms.SmsSender;
import com.visiondrive.util.VerificationCodeStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.concurrent.ThreadLocalRandom;

/**
 * 验证码业务服务：生成、发送、校验
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class VerificationCodeService {

    private final VerificationCodeStore store;
    private final SmsSender smsSender;

    @Value("${sms.provider:mock}")
    private String smsProvider;

    /**
     * 发送验证码
     */
    public SendResult sendCode(String phone) {
        if (!isValidPhone(phone)) {
            return SendResult.fail("手机号格式不正确");
        }

        String code = String.format("%06d", ThreadLocalRandom.current().nextInt(1000000));

        Long blocked = store.saveCode(phone, code);
        if (blocked != null) {
            if (blocked == -1) {
                return SendResult.fail("今日发送次数已达上限，请明天再试");
            }
            return SendResult.retryAfter(blocked);
        }

        boolean sent = smsSender.send(phone, code);
        if (!sent) {
            return SendResult.fail("验证码发送失败，请稍后重试");
        }

        log.info("验证码已发送: phone={}", phone.substring(0, 3) + "****");

        // Mock 模式下返回验证码便于调试
        if ("mock".equals(smsProvider)) {
            return SendResult.okWithMockCode(code);
        }
        return SendResult.ok();
    }

    /**
     * 校验验证码
     * @return null=校验通过, 否则返回错误消息
     */
    public String verifyCode(String phone, String code) {
        return store.verifyCode(phone, code);
    }

    private boolean isValidPhone(String phone) {
        return phone != null && phone.matches("^1[3-9]\\d{9}$");
    }

    /**
     * 发送结果
     */
    public static class SendResult {
        public boolean success;
        public String message;
        public Long retryAfter;
        public String mockCode; // 仅 mock 模式返回验证码

        public static SendResult ok() {
            SendResult r = new SendResult();
            r.success = true;
            r.message = "验证码已发送";
            return r;
        }

        public static SendResult okWithMockCode(String code) {
            SendResult r = ok();
            r.mockCode = code;
            return r;
        }

        public static SendResult fail(String msg) {
            SendResult r = new SendResult();
            r.success = false;
            r.message = msg;
            return r;
        }

        public static SendResult retryAfter(long seconds) {
            SendResult r = new SendResult();
            r.success = false;
            r.message = "发送过于频繁，请 " + seconds + " 秒后再试";
            r.retryAfter = seconds;
            return r;
        }
    }
}
