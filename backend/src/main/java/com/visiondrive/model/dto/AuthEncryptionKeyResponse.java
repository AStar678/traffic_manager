package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "认证请求加密公钥")
public record AuthEncryptionKeyResponse(
        @Schema(description = "公钥指纹") String keyId,
        @Schema(description = "密钥加密算法") String keyAlgorithm,
        @Schema(description = "请求内容加密算法") String contentAlgorithm,
        @Schema(description = "SubjectPublicKeyInfo PEM 格式公钥") String publicKey
) {
}
