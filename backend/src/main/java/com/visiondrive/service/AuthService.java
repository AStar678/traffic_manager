package com.visiondrive.service;

import com.visiondrive.common.exception.BusinessException;
import com.visiondrive.model.dto.LoginRequest;
import com.visiondrive.model.dto.LoginResponse;
import com.visiondrive.model.dto.RegisterRequest;
import com.visiondrive.model.dto.VerificationCodePurpose;
import com.visiondrive.model.entity.User;
import com.visiondrive.repository.UserRepository;
import com.visiondrive.security.JwtService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.dao.DataIntegrityViolationException;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final SystemLogService systemLogService;
    private final VerificationCodeService verificationCodeService;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> {
                    systemLogService.warn("auth", "unauthorized", Map.of(
                            "username", Objects.toString(request.getUsername(), ""),
                            "reason", "用户不存在"
                    ));
                    return new BusinessException(401, "用户名或密码错误");
                });

        if (!passwordMatches(request.getPassword(), user.getPassword())) {
            systemLogService.warn("auth", "unauthorized", Map.of(
                    "username", Objects.toString(request.getUsername(), ""),
                    "reason", "密码错误",
                    "userId", user.getId()
            ));
            throw new BusinessException(401, "用户名或密码错误");
        }

        if (passwordEncoder.upgradeEncoding(user.getPassword())) {
            user.setPassword(passwordEncoder.encode(request.getPassword()));
        }

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);
        systemLogService.info("auth", "login_success", Map.of(
                "username", user.getUsername(),
                "userId", user.getId()
        ));
        return buildLoginResponse(user);
    }

    /** 手机号验证码登录。未注册手机号必须先走正式注册流程。 */
    public LoginResponse loginByCode(String phone, String code) {
        User user = userRepository.findByPhone(phone)
                .orElseThrow(() -> new BusinessException(404, "该手机号尚未注册，请先注册"));

        String error = verificationCodeService.verifyCode(phone, VerificationCodePurpose.LOGIN, code);
        if (error != null) {
            systemLogService.warn("auth", "sms_code_rejected", Map.of(
                    "phone", maskPhone(phone),
                    "reason", error
            ));
            throw new BusinessException(401, error);
        }

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);
        systemLogService.info("auth", "sms_login_success", Map.of(
                "phone", maskPhone(phone),
                "userId", user.getId()
        ));
        return buildLoginResponse(user);
    }

    public LoginResponse register(RegisterRequest request) {
        if (userRepository.findByUsername(request.getUsername()).isPresent()) {
            throw new BusinessException(409, "用户名已存在");
        }
        if (userRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new BusinessException(409, "邮箱已存在");
        }
        if (userRepository.findByPhone(request.getPhone()).isPresent()) {
            throw new BusinessException(409, "手机号已存在");
        }

        String error = verificationCodeService.verifyCode(
                request.getPhone(),
                VerificationCodePurpose.REGISTER,
                request.getCode()
        );
        if (error != null) {
            throw new BusinessException(400, error);
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setEmail(request.getEmail());
        user.setPhone(request.getPhone());
        user.setNickname(request.getUsername());
        user.setRole("USER");
        user.setCreatedAt(LocalDateTime.now());
        user.setLastLoginAt(LocalDateTime.now());

        try {
            userRepository.saveAndFlush(user);
        } catch (DataIntegrityViolationException exception) {
            throw new BusinessException(409, "用户名、邮箱或手机号已被使用");
        }
        systemLogService.info("user_operation", "register", Map.of(
                "username", user.getUsername(),
                "email", Objects.toString(user.getEmail(), "")
        ));
        log.info("用户注册成功: {}", user.getUsername());
        return buildLoginResponse(user);
    }

    public void validateCodeSend(String phone, VerificationCodePurpose purpose) {
        boolean registered = userRepository.findByPhone(phone).isPresent();
        if (purpose == VerificationCodePurpose.REGISTER && registered) {
            throw new BusinessException(409, "该手机号已注册，请直接登录");
        }
        if (purpose == VerificationCodePurpose.LOGIN && !registered) {
            throw new BusinessException(404, "该手机号尚未注册，请先注册");
        }
    }

    public LoginResponse getProfile(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new BusinessException(404, "用户不存在"));
        return buildLoginResponse(user, false);
    }

    private LoginResponse buildLoginResponse(User user) {
        return buildLoginResponse(user, true);
    }

    private LoginResponse buildLoginResponse(User user, boolean includeToken) {
        LoginResponse response = new LoginResponse();
        response.setToken(includeToken ? jwtService.generateToken(user) : null);
        response.setUsername(user.getUsername());
        response.setUserId(user.getId());
        response.setNickname(user.getNickname() == null ? user.getUsername() : user.getNickname());
        response.setPhone(maskPhone(user.getPhone()));
        response.setEmail(user.getEmail());
        response.setRole(user.getRole() == null ? "USER" : user.getRole());
        return response;
    }

    private boolean passwordMatches(String rawPassword, String storedPassword) {
        if (storedPassword == null || !storedPassword.matches("^\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}$")) {
            return false;
        }
        return passwordEncoder.matches(rawPassword, storedPassword);
    }

    private String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }
}
