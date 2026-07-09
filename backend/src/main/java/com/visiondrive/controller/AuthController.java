package com.visiondrive.controller;

import com.visiondrive.model.dto.*;
import com.visiondrive.service.AuthService;
import com.visiondrive.service.VerificationCodeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping({"/api/auth", "/api/v1/auth"})
@RequiredArgsConstructor
@Tag(name = "用户认证", description = "登录、注册、短信验证码")
public class AuthController {

    private final AuthService authService;
    private final VerificationCodeService verificationCodeService;

    @Operation(summary = "用户登录")
    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.success(authService.login(request));
    }

    @Operation(summary = "用户注册")
    @PostMapping("/register")
    public ApiResponse<Void> register(@Valid @RequestBody RegisterRequest request) {
        authService.register(request);
        return ApiResponse.success();
    }

    @Operation(summary = "发送短信验证码")
    @PostMapping("/send-code")
    public ApiResponse<Map<String, Object>> sendCode(@Valid @RequestBody SendCodeRequest request) {
        VerificationCodeService.SendResult result = verificationCodeService.sendCode(request.getPhone());
        if (result.success) {
            Map<String, Object> data = new java.util.HashMap<>();
            data.put("retryAfter", 60);
            if (result.mockCode != null) data.put("mockCode", result.mockCode);
            return ApiResponse.success(data);
        }
        if (result.retryAfter != null) {
            return ApiResponse.error(429, result.message);
        }
        return ApiResponse.error(400, result.message);
    }

    @Operation(summary = "验证码登录（首次自动注册）")
    @PostMapping("/login/code")
    public ApiResponse<LoginResponse> loginByCode(@Valid @RequestBody CodeLoginRequest request) {
        return ApiResponse.success(authService.loginByCode(request.getPhone(), request.getCode()));
    }
}
