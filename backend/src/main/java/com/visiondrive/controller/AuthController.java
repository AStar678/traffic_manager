package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.LoginRequest;
import com.visiondrive.model.dto.LoginResponse;
import com.visiondrive.model.dto.RegisterRequest;
import com.visiondrive.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping({"/api/v1/auth"})
@RequiredArgsConstructor
@Tag(name = "用户认证", description = "登录、注册、Token管理")
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "用户登录")
    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return ApiResponse.success(response);
    }

    @Operation(summary = "用户注册")
    @PostMapping("/register")
    public ApiResponse<Void> register(@Valid @RequestBody RegisterRequest request) {
        authService.register(request);
        return ApiResponse.success();
    }
}
