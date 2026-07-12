package com.visiondrive.controller;

import com.visiondrive.model.dto.*;
import com.visiondrive.service.AuthService;
import com.visiondrive.service.VerificationCodeService;
import com.visiondrive.security.AuthenticatedUser;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping({"/api/v1/auth"})
@RequiredArgsConstructor
@Tag(name = "用户认证", description = "账号密码登录、短信验证码登录和注册")
public class AuthController {

    private final AuthService authService;
    private final VerificationCodeService verificationCodeService;

    @Operation(summary = "用户登录")
    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return ApiResponse.success(response);
    }

    @Operation(summary = "用户注册")
    @PostMapping("/register")
    public ApiResponse<LoginResponse> register(@Valid @RequestBody RegisterRequest request) {
        return ApiResponse.success(authService.register(request));
    }

    @Operation(summary = "发送短信验证码")
    @PostMapping("/send-code")
    public ResponseEntity<ApiResponse<Map<String, Object>>> sendCode(@Valid @RequestBody SendCodeRequest request) {
        authService.validateCodeSend(request.getPhone(), request.getPurpose());
        VerificationCodeService.SendResult result = verificationCodeService.sendCode(
                request.getPhone(),
                request.getPurpose()
        );
        Map<String, Object> data = new HashMap<>();
        if (result.retryAfter() != null) {
            data.put("retryAfter", result.retryAfter());
        }
        if (result.mockCode() != null) {
            data.put("mockCode", result.mockCode());
        }
        if (!result.success()) {
            ApiResponse<Map<String, Object>> response = ApiResponse.error(result.code(), result.message());
            response.setData(data);
            return ResponseEntity.status(result.code()).body(response);
        }
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @Operation(summary = "短信验证码登录")
    @PostMapping("/login/code")
    public ApiResponse<LoginResponse> loginByCode(@Valid @RequestBody CodeLoginRequest request) {
        return ApiResponse.success(authService.loginByCode(request.getPhone(), request.getCode()));
    }

    @Operation(summary = "获取当前登录用户")
    @GetMapping("/me")
    public ApiResponse<LoginResponse> me(@AuthenticationPrincipal AuthenticatedUser principal) {
        return ApiResponse.success(authService.getProfile(principal.id()));
    }
}
