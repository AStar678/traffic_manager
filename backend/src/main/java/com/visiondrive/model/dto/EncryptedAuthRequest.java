package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
@Schema(description = "RSA-OAEP + AES-GCM 混合加密的认证请求")
public class EncryptedAuthRequest {

    @NotBlank(message = "密钥标识不能为空")
    @Size(min = 8, max = 64, message = "密钥标识格式不正确")
    @Schema(description = "服务器公钥指纹")
    private String keyId;

    @NotBlank(message = "加密会话密钥不能为空")
    @Size(max = 1024, message = "加密会话密钥过长")
    @Schema(description = "RSA-OAEP-SHA256 加密的 AES-256 会话密钥（Base64）")
    private String encryptedKey;

    @NotBlank(message = "加密向量不能为空")
    @Size(max = 64, message = "加密向量过长")
    @Schema(description = "AES-GCM 96 位随机 IV（Base64）")
    private String iv;

    @NotBlank(message = "密文不能为空")
    @Size(max = 32768, message = "密文过长")
    @Schema(description = "AES-256-GCM 密文与 128 位认证标签（Base64）")
    private String ciphertext;
}
