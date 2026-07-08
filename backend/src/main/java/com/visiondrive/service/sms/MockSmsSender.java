package com.visiondrive.service.sms;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * Mock 短信发送器 —— 开发环境使用，验证码打印到控制台
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "sms.provider", havingValue = "mock", matchIfMissing = true)
public class MockSmsSender implements SmsSender {

    @Override
    public boolean send(String phone, String code) {
        log.info("========================================");
        log.info("  [Mock短信] 手机号: {}", phone);
        log.info("  [Mock短信] 验证码: {}", code);
        log.info("  [Mock短信] 有效期: 5分钟");
        log.info("========================================");
        return true;
    }
}
