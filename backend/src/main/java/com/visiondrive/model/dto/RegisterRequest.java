package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "注册请求")
public class RegisterRequest {
    @Schema(description = "用户名", example = "13800138000")
    private String username;

    @Schema(description = "手机号", example = "13800138000")
    private String phone;

    @Schema(description = "短信验证码")
    private String smsCode;

    @Schema(description = "密码", example = "Abc123456")
    @NotBlank(message = "密码不能为空")
    private String password;

    @Schema(description = "邮箱", example = "user@example.com")
    private String email;
}
