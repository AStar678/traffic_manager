package com.visiondrive.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class EvidenceProxyServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void readsUploadedEvidenceFile() throws Exception {
        RestTemplate restTemplate = new RestTemplate();
        EvidenceProxyService service = service(restTemplate);
        Path imageDir = tempDir.resolve("uploads/images/2026-07-13");
        Files.createDirectories(imageDir);
        Files.write(imageDir.resolve("failure.png"), new byte[]{1, 2, 3});

        ResponseEntity<byte[]> response = service.load("/api/files/images/2026-07-13/failure.png");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.IMAGE_PNG);
        assertThat(response.getBody()).containsExactly(1, 2, 3);
    }

    @Test
    void proxiesAllowedLoopbackEvidence() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        EvidenceProxyService service = service(restTemplate);

        server.expect(requestTo("http://127.0.0.1:8010/api/v1/cameras/snapshot.png"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(new byte[]{9, 8}, MediaType.IMAGE_PNG));

        ResponseEntity<byte[]> response = service.load("http://127.0.0.1:8010/api/v1/cameras/snapshot.png");

        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.IMAGE_PNG);
        assertThat(response.getBody()).containsExactly(9, 8);
        server.verify();
    }

    @Test
    void rejectsLocalPathOutsideAllowedDirectories() {
        RestTemplate restTemplate = new RestTemplate();
        EvidenceProxyService service = service(restTemplate);

        assertThatThrownBy(() -> service.load(tempDir.resolve("secret.png").toString()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("超出允许目录");
    }

    private EvidenceProxyService service(RestTemplate restTemplate) {
        EvidenceProxyService service = new EvidenceProxyService(restTemplate);
        ReflectionTestUtils.setField(service, "uploadDir", tempDir.resolve("uploads").toString());
        ReflectionTestUtils.setField(service, "cameraFrameDir", tempDir.resolve("uploads/camera-frames").toString());
        ReflectionTestUtils.setField(service, "allowedHosts", "localhost,127.0.0.1,::1");
        return service;
    }
}
