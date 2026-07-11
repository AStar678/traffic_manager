package com.visiondrive.service;

import com.visiondrive.common.exception.BusinessException;
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
        String account = request.getUsername();
        // 支持手机号或用户名登录
        User user = userRepository.findByPhone(account)
                .orElseGet(() -> userRepository.findByUsername(account)
                        .orElseThrow(() -> new BusinessException(400, "用户不存在")));

        if (!user.getPassword().equals(request.getPassword())) {
            throw new BusinessException(400, "密码错误");
        }

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);
        return buildResponse(user);
    }

    /** 手机号 + 验证码 → 重置密码（验证通过后直接修改密码） */
    public void resetPassword(String phone, String code, String newPassword) {
        String error = verificationCodeService.verifyCode(phone, code);
        if (error != null) throw new BusinessException(400, error);

        User user = userRepository.findByPhone(phone)
                .orElseThrow(() -> new BusinessException(400, "该手机号未注册"));
        user.setPassword(newPassword);
        userRepository.save(user);
        log.info("密码重置成功: phone={}", maskPhone(phone));
    }

    public LoginResponse loginByCode(String phone, String code) {
        String error = verificationCodeService.verifyCode(phone, code);
        if (error != null) throw new BusinessException(400, error);

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
        return buildResponse(user);
    }

    public void register(RegisterRequest request) {
        String phone = request.getPhone();
        if (phone != null && !phone.isBlank()) {
            // 手机号注册：校验验证码
            if (request.getSmsCode() == null || request.getSmsCode().isBlank())
                throw new BusinessException(400, "验证码不能为空");
            String err = verificationCodeService.verifyCode(phone, request.getSmsCode());
            if (err != null) throw new BusinessException(400, err);
            if (userRepository.findByPhone(phone).isPresent())
                throw new BusinessException(400, "该手机号已注册");
        }

        String username = request.getUsername();
        if (username == null || username.isBlank()) {
            username = phone != null ? phone : "user" + System.currentTimeMillis() % 10000;
        }

        if (userRepository.findByUsername(username).isPresent())
            throw new BusinessException(400, "用户名已存在");

        User user = new User();
        user.setUsername(username);
        user.setPassword(request.getPassword());
        user.setEmail(request.getEmail());
        user.setPhone(phone);
        user.setNickname(username);
        user.setRole("USER");
        user.setCreatedAt(LocalDateTime.now());
        userRepository.save(user);
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

    public boolean isPhoneRegistered(String phone) {
        return phone != null && userRepository.findByPhone(phone).isPresent();
    }
}
