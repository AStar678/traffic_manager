package com.visiondrive.service;

import com.visiondrive.model.dto.VerificationCodePurpose;
import com.visiondrive.service.sms.SmsSender;
import com.visiondrive.util.VerificationCodeStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;

@Slf4j
@Service
@RequiredArgsConstructor
public class VerificationCodeService {

    private final VerificationCodeStore store;
    private final SmsSender smsSender;
    private final SecureRandom random = new SecureRandom();

    @Value("${sms.expose-mock-code:false}")
    private boolean exposeMockCode;

    @Value("${sms.provider:mock}")
    private String provider;

    public SendResult sendCode(String phone, VerificationCodePurpose purpose) {
        String code = String.format("%06d", random.nextInt(1_000_000));
        VerificationCodeStore.SaveResult saved = store.saveCode(phone, purpose, code);
        if (!saved.saved()) {
            if (saved.dailyLimitReached()) {
                return SendResult.failure(429, "今日发送次数已达上限，请明天再试", null);
            }
            return SendResult.failure(429, "发送过于频繁，请稍后再试", saved.retryAfter());
        }

        if (!smsSender.send(phone, code)) {
            store.rollbackCode(phone, purpose, code);
            return SendResult.failure(503, "验证码发送失败，请稍后重试", null);
        }

        log.info("短信验证码已发送: phone={}, purpose={}", maskPhone(phone), purpose);
        String mockCode = exposeMockCode && "mock".equalsIgnoreCase(provider) ? code : null;
        return SendResult.success(mockCode);
    }

    public String verifyCode(String phone, VerificationCodePurpose purpose, String code) {
        return store.verifyCode(phone, purpose, code);
    }

    private String maskPhone(String phone) {
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    public record SendResult(boolean success, int code, String message, Long retryAfter, String mockCode) {
        static SendResult success(String mockCode) {
            return new SendResult(true, 0, "验证码已发送", 60L, mockCode);
        }

        static SendResult failure(int code, String message, Long retryAfter) {
            return new SendResult(false, code, message, retryAfter, null);
        }
    }
}
