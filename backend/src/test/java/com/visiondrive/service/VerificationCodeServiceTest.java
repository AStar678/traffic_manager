package com.visiondrive.service;

import com.visiondrive.model.dto.VerificationCodePurpose;
import com.visiondrive.service.sms.SmsSender;
import com.visiondrive.util.VerificationCodeStore;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;

class VerificationCodeServiceTest {

    @Test
    void mockSendReturnsDynamicCodeThatCanBeVerified() {
        SmsSender sender = (phone, code) -> true;
        VerificationCodeService service = new VerificationCodeService(new VerificationCodeStore(), sender);
        ReflectionTestUtils.setField(service, "provider", "mock");
        ReflectionTestUtils.setField(service, "exposeMockCode", true);

        VerificationCodeService.SendResult result = service.sendCode(
                "13800138000", VerificationCodePurpose.REGISTER
        );

        assertTrue(result.success());
        assertNotNull(result.mockCode());
        assertTrue(result.mockCode().matches("\\d{6}"));
        assertNull(service.verifyCode(
                "13800138000", VerificationCodePurpose.REGISTER, result.mockCode()
        ));
        assertNotNull(service.verifyCode(
                "13800138000", VerificationCodePurpose.REGISTER, result.mockCode()
        ));
    }
}
