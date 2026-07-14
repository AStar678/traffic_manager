package com.visiondrive.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.common.exception.BusinessException;
import com.visiondrive.model.dto.AuthEncryptionKeyResponse;
import com.visiondrive.model.dto.EncryptedAuthRequest;
import com.visiondrive.model.dto.LoginRequest;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.OAEPParameterSpec;
import javax.crypto.spec.PSource;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.spec.MGF1ParameterSpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AuthPayloadEncryptionServiceTest {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static AuthPayloadEncryptionService encryptionService;

    @BeforeAll
    static void createEncryptionService() {
        encryptionService = new AuthPayloadEncryptionService(OBJECT_MAPPER, "");
    }

    @Test
    void decryptsRsaOaepAndAesGcmEnvelope() throws Exception {
        LoginRequest login = new LoginRequest();
        login.setUsername("encrypted_user");
        login.setPassword("password123");

        EncryptedAuthRequest encrypted = encrypt(login, encryptionService.publicKeyResponse());
        LoginRequest decrypted = encryptionService.decrypt(encrypted, LoginRequest.class);

        assertEquals("encrypted_user", decrypted.getUsername());
        assertEquals("password123", decrypted.getPassword());
    }

    @Test
    void rejectsTamperedCiphertextWithoutLeakingCryptoDetails() throws Exception {
        LoginRequest login = new LoginRequest();
        login.setUsername("encrypted_user");
        login.setPassword("password123");
        EncryptedAuthRequest encrypted = encrypt(login, encryptionService.publicKeyResponse());
        byte[] ciphertext = Base64.getDecoder().decode(encrypted.getCiphertext());
        ciphertext[0] ^= 1;
        encrypted.setCiphertext(Base64.getEncoder().encodeToString(ciphertext));

        BusinessException exception = assertThrows(
                BusinessException.class,
                () -> encryptionService.decrypt(encrypted, LoginRequest.class)
        );

        assertEquals(400, exception.getCode());
        assertEquals("加密认证请求无效或密钥已更新，请刷新页面后重试", exception.getMessage());
    }

    private static EncryptedAuthRequest encrypt(Object payload, AuthEncryptionKeyResponse keyInfo) throws Exception {
        byte[] aesKey = new byte[32];
        byte[] iv = new byte[12];
        SecureRandom random = new SecureRandom();
        random.nextBytes(aesKey);
        random.nextBytes(iv);

        Cipher aes = Cipher.getInstance("AES/GCM/NoPadding");
        aes.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(aesKey, "AES"), new GCMParameterSpec(128, iv));
        aes.updateAAD(keyInfo.keyId().getBytes(StandardCharsets.UTF_8));
        byte[] ciphertext = aes.doFinal(OBJECT_MAPPER.writeValueAsBytes(payload));

        Cipher rsa = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        rsa.init(Cipher.ENCRYPT_MODE, parsePublicKey(keyInfo.publicKey()), new OAEPParameterSpec(
                "SHA-256", "MGF1", MGF1ParameterSpec.SHA256, PSource.PSpecified.DEFAULT
        ));

        EncryptedAuthRequest request = new EncryptedAuthRequest();
        request.setKeyId(keyInfo.keyId());
        request.setEncryptedKey(Base64.getEncoder().encodeToString(rsa.doFinal(aesKey)));
        request.setIv(Base64.getEncoder().encodeToString(iv));
        request.setCiphertext(Base64.getEncoder().encodeToString(ciphertext));
        return request;
    }

    private static PublicKey parsePublicKey(String pem) throws Exception {
        String encoded = pem
                .replace("-----BEGIN PUBLIC KEY-----", "")
                .replace("-----END PUBLIC KEY-----", "")
                .replaceAll("\\s", "");
        return KeyFactory.getInstance("RSA").generatePublic(
                new X509EncodedKeySpec(Base64.getDecoder().decode(encoded))
        );
    }
}
