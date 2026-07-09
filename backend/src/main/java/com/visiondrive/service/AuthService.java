package com.visiondrive.service;

import com.visiondrive.model.dto.LoginRequest;
import com.visiondrive.model.dto.LoginResponse;
import com.visiondrive.model.dto.RegisterRequest;
import com.visiondrive.model.entity.User;
import com.visiondrive.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final SystemLogService systemLogService;
    private final VerificationCodeService verificationCodeService;

    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> {
                    systemLogService.warn("auth", "unauthorized", Map.of(
                            "username", Objects.toString(request.getUsername(), ""),
                            "reason", "用户不存在"
                    ));
                    return new RuntimeException("用户不存在");
                });

        if (!user.getPassword().equals(request.getPassword())) {
            systemLogService.warn("auth", "unauthorized", Map.of(
                    "username", Objects.toString(request.getUsername(), ""),
                    "reason", "密码错误",
                    "userId", user.getId()
            ));
            throw new RuntimeException("密码错误");
        }

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);

        systemLogService.info("auth", "login_success", Map.of(
                "username", user.getUsername(),
                "userId", user.getId()
        ));
        return buildResponse(user);
    }

    public LoginResponse loginByCode(String phone, String code) {
        String error = verificationCodeService.verifyCode(phone, code);
        if (error != null) throw new RuntimeException(error);

        User user = userRepository.findByPhone(phone).orElseGet(() -> {
            User u = new User();
            u.setUsername("u" + phone);
            u.setPhone(phone);
            u.setPassword(UUID.randomUUID().toString());
            u.setNickname("用户" + phone.substring(phone.length() - 4));
            u.setRole("USER");
            u.setCreatedAt(LocalDateTime.now());
            return userRepository.save(u);
        });

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);

        systemLogService.info("auth", "code_login", Map.of(
                "phone", maskPhone(phone),
                "userId", user.getId()
        ));
        return buildResponse(user);
    }

    public void register(RegisterRequest request) {
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            throw new RuntimeException("用户名已存在");
        }
        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(request.getPassword());
        user.setEmail(request.getEmail());
        user.setNickname(request.getUsername());
        user.setRole("USER");
        user.setCreatedAt(LocalDateTime.now());
        userRepository.save(user);
        systemLogService.info("user_operation", "register", Map.of(
                "username", user.getUsername(),
                "email", Objects.toString(user.getEmail(), "")
        ));
        log.info("用户注册成功: {}", user.getUsername());
    }

    private LoginResponse buildResponse(User user) {
        LoginResponse r = new LoginResponse();
        r.setToken(UUID.randomUUID().toString());
        r.setUsername(user.getUsername());
        r.setUserId(user.getId());
        r.setNickname(user.getNickname() != null ? user.getNickname() : user.getUsername());
        r.setPhone(user.getPhone() != null ? maskPhone(user.getPhone()) : null);
        r.setRole(user.getRole() != null ? user.getRole() : "USER");
        return r;
    }

    private String maskPhone(String phone) {
        return phone != null && phone.length() >= 7 ? phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4) : phone;
    }
}
