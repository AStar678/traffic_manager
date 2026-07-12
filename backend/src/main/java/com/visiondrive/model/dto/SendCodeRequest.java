package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
@Schema(description = "发送短信验证码请求")
public class SendCodeRequest {

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    @Schema(description = "中国大陆手机号", example = "13800138000")
    private String phone;

    @NotNull(message = "验证码用途不能为空")
    @Schema(description = "验证码用途", example = "REGISTER")
    private VerificationCodePurpose purpose;
}
