package com.visiondrive.security;

import com.visiondrive.model.entity.User;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JwtServiceTest {

    @Test
    void signedTokenCarriesUserIdAndRejectsTampering() {
        JwtService service = new JwtService(
                "test-only-jwt-secret-with-at-least-thirty-two-bytes",
                60_000
        );
        User user = new User();
        user.setId(42L);
        user.setUsername("test-user");
        user.setRole("USER");

        String token = service.generateToken(user);

        assertTrue(service.isValid(token));
        assertEquals(42L, service.extractUserId(token));
        assertFalse(service.isValid(token.substring(0, token.length() - 1) + "x"));
    }
}
