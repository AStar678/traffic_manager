package com.visiondrive.agent;

import com.visiondrive.service.SystemLogService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

/**
 * 使用阿里千问视觉模型对车牌/交警手势失败样本做二次复核。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class QwenVisionReviewer {

    private static final List<String> VIDEO_EXTENSIONS = List.of("mp4", "avi", "mov", "mkv", "flv", "wmv");

    private final RestTemplate restTemplate;
    private final SystemLogService systemLogService;

    @Value("${llm.api-key:}")
    private String apiKey;

    @Value("${llm.vision-model:qwen3.7-plus}")
    private String visionModel;

    @Value("${llm.base-url:https://dashscope.aliyuncs.com/compatible-mode/v1}")
    private String baseUrl;

    @Value("${llm.vision-max-base64-bytes:7340032}")
    private long maxBase64Bytes;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Value("${file.public-base-url:}")
    private String publicBaseUrl;

    public ReviewResult review(String taskType, String evidenceUrl, Double confidence, String failureReason) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException("未配置 DASHSCOPE_API_KEY");
        }

        long startedAt = System.currentTimeMillis();
        Map<String, Object> logDetail = new LinkedHashMap<>();
        logDetail.put("taskType", taskType);
        logDetail.put("model", visionModel);
        logDetail.put("evidenceUrl", evidenceUrl);

        try {
            Evidence evidence = resolveEvidence(evidenceUrl);
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);

            Map<String, Object> media = new LinkedHashMap<>();
            if (evidence.video()) {
                media.put("type", "video_url");
                media.put("video_url", Map.of("url", evidence.value()));
                media.put("fps", 1);
            } else {
                media.put("type", "image_url");
                media.put("image_url", Map.of("url", evidence.value()));
            }

            Map<String, Object> requestBody = new LinkedHashMap<>();
            requestBody.put("model", visionModel);
            requestBody.put("temperature", 0.1);
            requestBody.put("messages", List.of(Map.of(
                    "role", "user",
                    "content", List.of(
                            media,
                            Map.of("type", "text", "text", buildPrompt(taskType, confidence, failureReason))
                    )
            )));

            ResponseEntity<Map> response = restTemplate.exchange(
                    endpoint(),
                    HttpMethod.POST,
                    new HttpEntity<>(requestBody, headers),
                    Map.class
            );
            String analysis = extractContent(response.getBody());
            long tokens = extractTotalTokens(response.getBody());
            if (analysis.isBlank()) {
                throw new IllegalStateException("千问视觉模型未返回复核结论");
            }

            logDetail.put("latencyMs", System.currentTimeMillis() - startedAt);
            logDetail.put("tokens", tokens);
            systemLogService.info("llm", "token_usage", logDetail);
            return new ReviewResult(analysis, visionModel, tokens);
        } catch (ResourceAccessException error) {
            logDetail.put("latencyMs", System.currentTimeMillis() - startedAt);
            logDetail.put("errorMessage", Objects.toString(error.getMessage(), ""));
            systemLogService.warn("llm", "timeout", logDetail);
            throw error;
        } catch (RuntimeException error) {
            logDetail.put("latencyMs", System.currentTimeMillis() - startedAt);
            logDetail.put("errorMessage", Objects.toString(error.getMessage(), ""));
            systemLogService.warn("llm", "failure", logDetail);
            throw error;
        }
    }

    private String buildPrompt(String taskType, Double confidence, String failureReason) {
        String target = "license_plate".equals(taskType) ? "道路车辆车牌" : "中国标准交警指挥手势";
        return """
                你是车载视觉识别复核 Agent。请检查这份%s识别失败样本。
                原模型置信度：%s
                原模型失败原因：%s
                请判断画面中是否存在目标、给出最可能的正确识别结果，并分析失败是否由模糊、遮挡、光照、角度、目标缺失或模型误判造成。
                仅输出中文复核结论，包含“复核结果、可能根因、建议处置”三项，总计不超过220字；不确定时必须明确说明，不得编造车牌字符或手势。
                """.formatted(
                target,
                confidence == null ? "未知" : String.format(Locale.ROOT, "%.3f", confidence),
                failureReason == null || failureReason.isBlank() ? "置信度低于阈值" : failureReason
        );
    }

    private Evidence resolveEvidence(String evidenceUrl) {
        if (evidenceUrl == null || evidenceUrl.isBlank()) {
            throw new IllegalArgumentException("失败样本地址为空");
        }
        boolean video = isVideo(evidenceUrl);
        if (isRemoteUrl(evidenceUrl) && !isLoopbackUrl(evidenceUrl)) {
            return new Evidence(evidenceUrl, video);
        }
        if (!publicBaseUrl.isBlank() && evidenceUrl.startsWith("/")) {
            return new Evidence(joinUrl(publicBaseUrl, evidenceUrl), video);
        }

        Path localPath = resolveLocalPath(evidenceUrl);
        try {
            long size = Files.size(localPath);
            if (size > maxBase64Bytes) {
                throw new IllegalArgumentException("本地失败样本超过 Base64 上限，请配置 FILE_PUBLIC_BASE_URL: " + size);
            }
            String mimeType = Objects.requireNonNullElse(Files.probeContentType(localPath), mimeType(localPath));
            String encoded = Base64.getEncoder().encodeToString(Files.readAllBytes(localPath));
            return new Evidence("data:" + mimeType + ";base64," + encoded, video);
        } catch (Exception error) {
            if (error instanceof RuntimeException runtimeException) {
                throw runtimeException;
            }
            throw new IllegalArgumentException("读取失败样本失败: " + error.getMessage(), error);
        }
    }

    private Path resolveLocalPath(String evidenceUrl) {
        String path = evidenceUrl;
        if (isRemoteUrl(evidenceUrl)) {
            path = URI.create(evidenceUrl).getPath();
        }
        String prefix = "/api/files/";
        if (path.startsWith(prefix)) {
            path = path.substring(prefix.length());
            Path root = Paths.get(uploadDir).toAbsolutePath().normalize();
            Path resolved = root.resolve(path).normalize();
            if (!resolved.startsWith(root)) {
                throw new IllegalArgumentException("失败样本路径超出上传目录");
            }
            return resolved;
        }
        return Paths.get(path).toAbsolutePath().normalize();
    }

    private boolean isRemoteUrl(String value) {
        return value.startsWith("http://") || value.startsWith("https://");
    }

    private boolean isLoopbackUrl(String value) {
        try {
            String host = URI.create(value).getHost();
            return "localhost".equalsIgnoreCase(host) || "127.0.0.1".equals(host) || "::1".equals(host);
        } catch (Exception ignored) {
            return false;
        }
    }

    private boolean isVideo(String value) {
        String path = value;
        try {
            if (isRemoteUrl(value)) path = URI.create(value).getPath();
        } catch (Exception ignored) {
            // 使用原值判断扩展名。
        }
        String extension = extension(path);
        return VIDEO_EXTENSIONS.contains(extension);
    }

    private String mimeType(Path path) {
        return switch (extension(path.getFileName().toString())) {
            case "mp4" -> "video/mp4";
            case "avi" -> "video/x-msvideo";
            case "mov" -> "video/quicktime";
            case "mkv" -> "video/x-matroska";
            case "png" -> "image/png";
            case "bmp" -> "image/bmp";
            default -> "image/jpeg";
        };
    }

    private String extension(String value) {
        int dot = value.lastIndexOf('.');
        return dot < 0 ? "" : value.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private String joinUrl(String base, String path) {
        return base.replaceFirst("/+$", "") + "/" + path.replaceFirst("^/+", "");
    }

    private String endpoint() {
        return baseUrl.replaceFirst("/+$", "") + "/chat/completions";
    }

    private String extractContent(Map<?, ?> responseBody) {
        if (responseBody == null || !(responseBody.get("choices") instanceof List<?> choices) || choices.isEmpty()) {
            return "";
        }
        Object first = choices.get(0);
        if (!(first instanceof Map<?, ?> choice) || !(choice.get("message") instanceof Map<?, ?> message)) {
            return "";
        }
        return Objects.toString(message.get("content"), "").trim();
    }

    private long extractTotalTokens(Map<?, ?> responseBody) {
        if (responseBody == null || !(responseBody.get("usage") instanceof Map<?, ?> usage)) return 0;
        Object value = usage.get("total_tokens");
        return value instanceof Number number ? number.longValue() : 0;
    }

    private record Evidence(String value, boolean video) {
    }

    public record ReviewResult(String analysis, String model, long tokens) {
    }
}
