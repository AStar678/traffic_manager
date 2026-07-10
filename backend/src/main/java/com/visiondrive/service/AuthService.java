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

    public LoginResponse login(LoginRequest request) {
        // 简化版：先查询用户
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> {
                    systemLogService.warn("auth", "unauthorized", Map.of(
                            "username", Objects.toString(request.getUsername(), ""),
                            "reason", "用户不存在"
                    ));
                    return new RuntimeException("用户不存在");
                });

        // 简化版：密码先明文对比（后续加加密）
        if (!user.getPassword().equals(request.getPassword())) {
            systemLogService.warn("auth", "unauthorized", Map.of(
                    "username", Objects.toString(request.getUsername(), ""),
                    "reason", "密码错误",
                    "userId", user.getId()
            ));
            throw new RuntimeException("密码错误");
        }

        // 简化版：生成临时 Token（后续替换为 JWT）
        String token = UUID.randomUUID().toString();
        systemLogService.info("auth", "login_success", Map.of(
                "username", user.getUsername(),
                "userId", user.getId()
        ));
        return new LoginResponse(token, user.getUsername());
    }

    public void register(RegisterRequest request) {
        // 检查用户名是否已存在
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            throw new RuntimeException("用户名已存在");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(request.getPassword());  // 后续加加密
        user.setEmail(request.getEmail());
        user.setCreatedAt(LocalDateTime.now());

        userRepository.save(user);
        systemLogService.info("user_operation", "register", Map.of(
                "username", user.getUsername(),
                "email", Objects.toString(user.getEmail(), "")
        ));
        log.info("用户注册成功: {}", user.getUsername());
    }
}
