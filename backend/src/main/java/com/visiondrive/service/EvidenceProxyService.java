package com.visiondrive.service;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class EvidenceProxyService {

    private final RestTemplate restTemplate;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Value("${camera.frame-dir:./uploads/camera-frames}")
    private String cameraFrameDir;

    @Value("${alert.evidence-proxy.allowed-hosts:localhost,127.0.0.1,::1}")
    private String allowedHosts;

    public ResponseEntity<byte[]> load(String source) {
        if (source == null || source.isBlank()) {
            throw new IllegalArgumentException("失败样本地址为空");
        }
        if (isRemoteUrl(source)) {
            return loadRemote(source);
        }
        return loadLocal(source);
    }

    private ResponseEntity<byte[]> loadRemote(String source) {
        URI uri = URI.create(source);
        String host = uri.getHost();
        if (host == null || !allowedHostSet().contains(host.toLowerCase(Locale.ROOT))) {
            throw new IllegalArgumentException("失败样本远程地址不在允许列表");
        }

        ResponseEntity<byte[]> response = restTemplate.exchange(
                uri,
                HttpMethod.GET,
                new HttpEntity<>(new HttpHeaders()),
                byte[].class
        );
        MediaType contentType = response.getHeaders().getContentType();
        if (contentType == null) {
            contentType = mediaType(uri.getPath());
        }
        return ResponseEntity
                .status(response.getStatusCode())
                .contentType(contentType)
                .body(response.getBody());
    }

    private ResponseEntity<byte[]> loadLocal(String source) {
        Path path = resolveLocalPath(source);
        if (!Files.isRegularFile(path)) {
            throw new IllegalArgumentException("失败样本文件不存在");
        }
        try {
            MediaType contentType = MediaType.parseMediaType(
                    Files.probeContentType(path) == null ? mediaType(path.toString()).toString() : Files.probeContentType(path)
            );
            return ResponseEntity
                    .ok()
                    .contentType(contentType)
                    .body(Files.readAllBytes(path));
        } catch (Exception error) {
            throw new IllegalArgumentException("读取失败样本失败: " + error.getMessage(), error);
        }
    }

    private Path resolveLocalPath(String source) {
        Path uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path frameRoot = Paths.get(cameraFrameDir).toAbsolutePath().normalize();
        Path resolved;

        if (source.startsWith("/api/files/")) {
            resolved = uploadRoot.resolve(source.substring("/api/files/".length())).normalize();
        } else {
            Path candidate = Paths.get(source);
            resolved = candidate.isAbsolute()
                    ? candidate.normalize()
                    : uploadRoot.resolve(candidate).normalize();
        }

        if (!resolved.startsWith(uploadRoot) && !resolved.startsWith(frameRoot)) {
            throw new IllegalArgumentException("失败样本路径超出允许目录");
        }
        return resolved;
    }

    private boolean isRemoteUrl(String source) {
        return source.startsWith("http://") || source.startsWith("https://");
    }

    private Set<String> allowedHostSet() {
        return Arrays.stream(allowedHosts.split(","))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .map(value -> value.toLowerCase(Locale.ROOT))
                .collect(Collectors.toSet());
    }

    private MediaType mediaType(String value) {
        String normalized = value.toLowerCase(Locale.ROOT);
        if (normalized.endsWith(".png")) return MediaType.IMAGE_PNG;
        if (normalized.endsWith(".gif")) return MediaType.IMAGE_GIF;
        if (normalized.endsWith(".bmp")) return MediaType.parseMediaType("image/bmp");
        if (normalized.endsWith(".webp")) return MediaType.parseMediaType("image/webp");
        if (normalized.endsWith(".mp4")) return MediaType.parseMediaType("video/mp4");
        if (normalized.endsWith(".mov")) return MediaType.parseMediaType("video/quicktime");
        if (normalized.endsWith(".avi")) return MediaType.parseMediaType("video/x-msvideo");
        return MediaType.IMAGE_JPEG;
    }
}
