package com.visiondrive.util;

import com.visiondrive.model.dto.VerificationCodePurpose;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class VerificationCodeStoreTest {

    @Test
    void codeIsSingleUseAndResendIsRateLimited() {
        VerificationCodeStore store = new VerificationCodeStore();

        VerificationCodeStore.SaveResult saved = store.saveCode(
                "13800138000", VerificationCodePurpose.LOGIN, "123456"
        );
        assertTrue(saved.saved());

        VerificationCodeStore.SaveResult repeated = store.saveCode(
                "13800138000", VerificationCodePurpose.LOGIN, "654321"
        );
        assertFalse(repeated.saved());
        assertNotNull(repeated.retryAfter());

        assertNull(store.verifyCode("13800138000", VerificationCodePurpose.LOGIN, "123456"));
        assertNotNull(store.verifyCode("13800138000", VerificationCodePurpose.LOGIN, "123456"));
    }

    @Test
    void codeIsInvalidatedAfterFiveWrongAttempts() {
        VerificationCodeStore store = new VerificationCodeStore();
        store.saveCode("13900139000", VerificationCodePurpose.LOGIN, "123456");

        for (int attempt = 0; attempt < VerificationCodeStore.MAX_ATTEMPTS; attempt++) {
            assertNotNull(store.verifyCode("13900139000", VerificationCodePurpose.LOGIN, "000000"));
        }

        assertEquals(
                "验证码已过期或未发送，请重新获取",
                store.verifyCode("13900139000", VerificationCodePurpose.LOGIN, "123456")
        );
    }

    @Test
    void registrationCodeCannotBeUsedForLogin() {
        VerificationCodeStore store = new VerificationCodeStore();
        store.saveCode("13700137000", VerificationCodePurpose.REGISTER, "123456");

        assertNotNull(store.verifyCode("13700137000", VerificationCodePurpose.LOGIN, "123456"));
        assertNull(store.verifyCode("13700137000", VerificationCodePurpose.REGISTER, "123456"));
    }

    @Test
    void cooldownIsSharedAcrossPurposes() {
        VerificationCodeStore store = new VerificationCodeStore();
        assertTrue(store.saveCode("13600136000", VerificationCodePurpose.LOGIN, "123456").saved());

        VerificationCodeStore.SaveResult registerAttempt = store.saveCode(
                "13600136000", VerificationCodePurpose.REGISTER, "654321"
        );

        assertFalse(registerAttempt.saved());
        assertNotNull(registerAttempt.retryAfter());
    }
}
