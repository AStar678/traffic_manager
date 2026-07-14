package com.visiondrive.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.common.exception.BusinessException;
import com.visiondrive.model.dto.AuthEncryptionKeyResponse;
import com.visiondrive.model.dto.EncryptedAuthRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.OAEPParameterSpec;
import javax.crypto.spec.PSource;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.interfaces.RSAPrivateCrtKey;
import java.security.interfaces.RSAPrivateKey;
import java.security.spec.MGF1ParameterSpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.RSAPublicKeySpec;
import java.util.Arrays;
import java.util.Base64;

@Slf4j
@Service
public class AuthPayloadEncryptionService {

    private static final int RSA_BITS = 3072;
    private static final int AES_KEY_BYTES = 32;
    private static final int GCM_IV_BYTES = 12;
    private static final int GCM_TAG_BITS = 128;
    private static final int MAX_CIPHERTEXT_BYTES = 24 * 1024;
    private static final OAEPParameterSpec OAEP_SHA256 = new OAEPParameterSpec(
            "SHA-256",
            "MGF1",
            MGF1ParameterSpec.SHA256,
            PSource.PSpecified.DEFAULT
    );

    private final ObjectMapper objectMapper;
    private final PrivateKey privateKey;
    private final PublicKey publicKey;
    private final String keyId;

    public AuthPayloadEncryptionService(
            ObjectMapper objectMapper,
            @Value("${auth.payload-encryption.private-key-path:}") String privateKeyPath
    ) {
        this.objectMapper = objectMapper;
        KeyPair keyPair = loadKeyPair(privateKeyPath);
        this.privateKey = keyPair.getPrivate();
        this.publicKey = keyPair.getPublic();
        this.keyId = fingerprint(publicKey);
        log.info("认证请求混合加密已启用: keyId={}, persistentKey={}", keyId,
                privateKeyPath != null && !privateKeyPath.isBlank());
    }

    public AuthEncryptionKeyResponse publicKeyResponse() {
        return new AuthEncryptionKeyResponse(
                keyId,
                "RSA-OAEP-256",
                "AES-256-GCM",
                toPublicKeyPem(publicKey)
        );
    }

    public <T> T decrypt(EncryptedAuthRequest request, Class<T> targetType) {
        byte[] aesKey = null;
        byte[] plaintext = null;
        try {
            if (!MessageDigest.isEqual(
                    keyId.getBytes(StandardCharsets.UTF_8),
                    request.getKeyId().getBytes(StandardCharsets.UTF_8)
            )) {
                throw invalidEncryptedRequest();
            }

            Base64.Decoder decoder = Base64.getDecoder();
            byte[] encryptedKey = decoder.decode(request.getEncryptedKey());
            byte[] iv = decoder.decode(request.getIv());
            byte[] ciphertext = decoder.decode(request.getCiphertext());
            int rsaBytes = (((RSAPrivateKey) privateKey).getModulus().bitLength() + 7) / 8;

            if (encryptedKey.length != rsaBytes
                    || iv.length != GCM_IV_BYTES
                    || ciphertext.length < GCM_TAG_BITS / 8
                    || ciphertext.length > MAX_CIPHERTEXT_BYTES) {
                throw invalidEncryptedRequest();
            }

            Cipher rsa = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
            rsa.init(Cipher.DECRYPT_MODE, privateKey, OAEP_SHA256);
            aesKey = rsa.doFinal(encryptedKey);
            if (aesKey.length != AES_KEY_BYTES) {
                throw invalidEncryptedRequest();
            }

            Cipher aes = Cipher.getInstance("AES/GCM/NoPadding");
            aes.init(Cipher.DECRYPT_MODE, new SecretKeySpec(aesKey, "AES"),
                    new GCMParameterSpec(GCM_TAG_BITS, iv));
            aes.updateAAD(keyId.getBytes(StandardCharsets.UTF_8));
            plaintext = aes.doFinal(ciphertext);
            return objectMapper.readValue(plaintext, targetType);
        } catch (BusinessException exception) {
            throw exception;
        } catch (Exception exception) {
            throw invalidEncryptedRequest();
        } finally {
            if (aesKey != null) Arrays.fill(aesKey, (byte) 0);
            if (plaintext != null) Arrays.fill(plaintext, (byte) 0);
        }
    }

    private KeyPair loadKeyPair(String privateKeyPath) {
        try {
            if (privateKeyPath == null || privateKeyPath.isBlank()) {
                log.warn("未配置认证加密私钥文件，本次进程使用临时 RSA 密钥");
                KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
                generator.initialize(RSA_BITS);
                return generator.generateKeyPair();
            }

            Path path = Path.of(privateKeyPath).toAbsolutePath().normalize();
            if (!Files.isRegularFile(path)) {
                throw new IllegalStateException("认证加密私钥不存在: " + path);
            }
            String pem = Files.readString(path, StandardCharsets.US_ASCII);
            String encoded = pem
                    .replace("-----BEGIN PRIVATE KEY-----", "")
                    .replace("-----END PRIVATE KEY-----", "")
                    .replaceAll("\\s", "");
            PrivateKey loadedPrivateKey = KeyFactory.getInstance("RSA")
                    .generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(encoded)));
            if (!(loadedPrivateKey instanceof RSAPrivateCrtKey rsaPrivateKey)) {
                throw new IllegalStateException("认证加密私钥必须为 RSA PKCS#8 CRT 格式");
            }
            PublicKey loadedPublicKey = KeyFactory.getInstance("RSA").generatePublic(
                    new RSAPublicKeySpec(rsaPrivateKey.getModulus(), rsaPrivateKey.getPublicExponent())
            );
            return new KeyPair(loadedPublicKey, loadedPrivateKey);
        } catch (IllegalStateException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new IllegalStateException("读取认证加密私钥失败", exception);
        }
    }

    private String fingerprint(PublicKey key) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(key.getEncoded());
            return Base64.getUrlEncoder().withoutPadding().encodeToString(Arrays.copyOf(digest, 18));
        } catch (Exception exception) {
            throw new IllegalStateException("计算认证公钥指纹失败", exception);
        }
    }

    private String toPublicKeyPem(PublicKey key) {
        String encoded = Base64.getMimeEncoder(64, new byte[]{'\n'}).encodeToString(key.getEncoded());
        return "-----BEGIN PUBLIC KEY-----\n" + encoded + "\n-----END PUBLIC KEY-----";
    }

    private BusinessException invalidEncryptedRequest() {
        return new BusinessException(400, "加密认证请求无效或密钥已更新，请刷新页面后重试");
    }
}
