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
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final VerificationCodeService verificationCodeService;

    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        if (!user.getPassword().equals(request.getPassword())) {
            throw new RuntimeException("密码错误");
        }

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);

        return buildLoginResponse(user);
    }

    /**
     * 短信验证码登录（首次自动注册）
     */
    public LoginResponse loginByCode(String phone, String code) {
        // 1. 校验验证码
        String error = verificationCodeService.verifyCode(phone, code);
        if (error != null) {
            throw new RuntimeException(error);
        }

        // 2. 查询或创建用户
        User user = userRepository.findByPhone(phone).orElseGet(() -> {
            User newUser = new User();
            newUser.setUsername("u" + phone);
            newUser.setPhone(phone);
            newUser.setPassword(UUID.randomUUID().toString()); // 随机密码
            newUser.setNickname("用户" + phone.substring(phone.length() - 4));
            newUser.setRole("USER");
            newUser.setCreatedAt(LocalDateTime.now());
            User saved = userRepository.save(newUser);
            log.info("新用户自动注册: phone={}", phone.substring(0, 3) + "****");
            return saved;
        });

        // 3. 更新登录时间
        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);

        return buildLoginResponse(user);
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
        log.info("用户注册成功: {}", user.getUsername());
    }

    private LoginResponse buildLoginResponse(User user) {
        String token = UUID.randomUUID().toString();
        LoginResponse resp = new LoginResponse();
        resp.setToken(token);
        resp.setUsername(user.getUsername());
        resp.setUserId(user.getId());
        resp.setNickname(user.getNickname() != null ? user.getNickname() : user.getUsername());
        resp.setPhone(user.getPhone() != null ? maskPhone(user.getPhone()) : null);
        resp.setRole(user.getRole() != null ? user.getRole() : "USER");
        return resp;
    }

    private String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) return phone;
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }
}