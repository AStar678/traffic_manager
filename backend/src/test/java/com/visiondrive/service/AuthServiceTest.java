package com.visiondrive.service;

import com.visiondrive.common.exception.BusinessException;
import com.visiondrive.model.dto.LoginResponse;
import com.visiondrive.model.dto.LoginRequest;
import com.visiondrive.model.dto.RegisterRequest;
import com.visiondrive.model.dto.VerificationCodePurpose;
import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.model.entity.User;
import com.visiondrive.repository.SystemLogRepository;
import com.visiondrive.repository.UserRepository;
import com.visiondrive.service.sms.SmsSender;
import com.visiondrive.security.JwtService;
import com.visiondrive.util.VerificationCodeStore;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.lang.reflect.Proxy;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class AuthServiceTest {

    @Test
    void plaintextDatabasePasswordIsNeverAcceptedByLogin() {
        TestFixture fixture = new TestFixture();
        User user = fixture.user("13800138000");
        user.setPassword("password123");
        fixture.storedUser.set(user);
        LoginRequest request = new LoginRequest();
        request.setUsername(user.getUsername());
        request.setPassword("password123");

        BusinessException exception = assertThrows(
                BusinessException.class,
                () -> fixture.authService.login(request)
        );

        assertEquals(401, exception.getCode());
    }

    @Test
    void unregisteredPhoneCannotBypassRegistrationWithCodeLogin() {
        TestFixture fixture = new TestFixture();
        VerificationCodeService.SendResult sent = fixture.verificationCodeService.sendCode(
                "13800138000", VerificationCodePurpose.LOGIN
        );

        BusinessException exception = assertThrows(
                BusinessException.class,
                () -> fixture.authService.loginByCode("13800138000", sent.mockCode())
        );

        assertEquals(404, exception.getCode());
        assertNull(fixture.storedUser.get());
    }

    @Test
    void wrongCodeNeverCreatesUser() {
        TestFixture fixture = new TestFixture();
        fixture.storedUser.set(fixture.user("13800138000"));
        VerificationCodeService.SendResult sent = fixture.verificationCodeService.sendCode(
                "13800138000", VerificationCodePurpose.LOGIN
        );
        String wrongCode = "000000".equals(sent.mockCode()) ? "999999" : "000000";

        BusinessException exception = assertThrows(
                BusinessException.class,
                () -> fixture.authService.loginByCode("13800138000", wrongCode)
        );

        assertEquals(401, exception.getCode());
        assertNotNull(fixture.storedUser.get());
    }

    @Test
    void registrationRequiresRegisterCodeAndReturnsToken() {
        TestFixture fixture = new TestFixture();
        VerificationCodeService.SendResult sent = fixture.verificationCodeService.sendCode(
                "13800138000", VerificationCodePurpose.REGISTER
        );
        RegisterRequest request = new RegisterRequest();
        request.setUsername("new_user");
        request.setEmail("new_user@example.com");
        request.setPassword("password123");
        request.setPhone("13800138000");
        request.setCode(sent.mockCode());

        LoginResponse response = fixture.authService.register(request);

        assertNotNull(response.getToken());
        assertEquals("138****8000", response.getPhone());
        assertEquals("new_user@example.com", response.getEmail());
        assertTrue(fixture.storedUser.get().getPassword().startsWith("$2"));
    }

    private static final class TestFixture {
        private final AtomicReference<User> storedUser = new AtomicReference<>();
        private final VerificationCodeService verificationCodeService;
        private final AuthService authService;

        private TestFixture() {
            UserRepository userRepository = proxy(UserRepository.class, (proxy, method, args) -> {
                return switch (method.getName()) {
                    case "findByPhone" -> Optional.ofNullable(storedUser.get());
                    case "findByUsername" -> {
                        User user = storedUser.get();
                        String username = (String) args[0];
                        yield user != null && username.equals(user.getUsername())
                                ? Optional.of(user)
                                : Optional.empty();
                    }
                    case "findByEmail" -> Optional.empty();
                    case "save", "saveAndFlush" -> {
                        User user = (User) args[0];
                        if (user.getId() == null) user.setId(42L);
                        storedUser.set(user);
                        yield user;
                    }
                    default -> defaultValue(method.getReturnType());
                };
            });

            SystemLogRepository systemLogRepository = proxy(SystemLogRepository.class, (proxy, method, args) -> {
                if ("save".equals(method.getName())) return (SystemLog) args[0];
                return defaultValue(method.getReturnType());
            });
            SystemLogService systemLogService = new SystemLogService(systemLogRepository);

            SmsSender sender = (phone, code) -> true;
            verificationCodeService = new VerificationCodeService(new VerificationCodeStore(), sender);
            ReflectionTestUtils.setField(verificationCodeService, "provider", "mock");
            ReflectionTestUtils.setField(verificationCodeService, "exposeMockCode", true);
            JwtService jwtService = new JwtService(
                    "test-only-jwt-secret-with-at-least-thirty-two-bytes",
                    7_200_000
            );
            authService = new AuthService(
                    userRepository,
                    systemLogService,
                    verificationCodeService,
                    new BCryptPasswordEncoder(),
                    jwtService
            );
        }

        private User user(String phone) {
            User user = new User();
            user.setId(42L);
            user.setUsername("existing_user");
            user.setPhone(phone);
            user.setEmail("existing@example.com");
            user.setPassword(new BCryptPasswordEncoder().encode("password123"));
            user.setRole("USER");
            return user;
        }
    }

    @SuppressWarnings("unchecked")
    private static <T> T proxy(Class<T> type, java.lang.reflect.InvocationHandler handler) {
        return (T) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, handler);
    }

    private static Object defaultValue(Class<?> type) {
        if (!type.isPrimitive()) return null;
        if (type == boolean.class) return false;
        if (type == byte.class) return (byte) 0;
        if (type == short.class) return (short) 0;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        if (type == float.class) return 0F;
        if (type == double.class) return 0D;
        if (type == char.class) return '\0';
        return null;
    }
}
