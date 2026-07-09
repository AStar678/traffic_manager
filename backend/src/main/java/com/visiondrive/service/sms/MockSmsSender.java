package com.visiondrive.service.sms;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@ConditionalOnProperty(name = "sms.provider", havingValue = "mock", matchIfMissing = true)
public class MockSmsSender implements SmsSender {
    @Override
    public boolean send(String phone, String code) {
        log.info("[Mock短信] phone={} code={} (5分钟有效)", phone.substring(0, 3) + "****", code);
        return true;
    }
}
