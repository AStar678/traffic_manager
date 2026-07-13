package com.visiondrive.client;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.InferenceResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class AlgorithmClient {

    public static final String OWNER_GESTURE_ALGORITHM = "dinov2_tcn_prototype";

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${algorithm.license.base-url:http://localhost:8000}")
    private String licenseAlgorithmBaseUrl;

    @Value("${algorithm.police.base-url:http://localhost:8001}")
    private String policeAlgorithmBaseUrl;

    @Value("${algorithm.gesture.base-url:http://localhost:8002}")
    private String gestureAlgorithmBaseUrl;

    @Value("${algorithm.vehicle.base-url:http://localhost:8004}")
    private String vehicleAlgorithmBaseUrl;

    @Value("${algorithm.inference.image:/api/v1/inference/image}")
    private String inferencePath;

    public InferenceResponse callImageInference(String taskType, String imageUrl) {
        return callInference(taskType, "image_url", imageUrl);
    }

    public InferenceResponse callFileInference(String taskType, String imagePath) {
        return callFileInference(taskType, imagePath, null);
    }

    public InferenceResponse callFileInference(String taskType, String imagePath, String sourceId) {
        return callFileInference(taskType, imagePath, sourceId, false);
    }

    public InferenceResponse callFileInference(
            String taskType,
            String imagePath,
            String sourceId,
            boolean includeVisuals
    ) {
        return callInference(taskType, "image_path", imagePath, sourceId, includeVisuals);
    }

    private InferenceResponse callInference(String taskType, String inputField, String inputValue) {
        return callInference(taskType, inputField, inputValue, null, null);
    }

    private InferenceResponse callInference(String taskType, String inputField, String inputValue, String sourceId) {
        return callInference(taskType, inputField, inputValue, sourceId, null);
    }

    private InferenceResponse callInference(
            String taskType,
            String inputField,
            String inputValue,
            String sourceId,
            Boolean includeVisuals
    ) {
        log.info("调用算法服务: taskType={}, inputField={}", taskType, inputField);

        String url = resolveInferenceBaseUrl(taskType) + inferencePath;
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("task_type", taskType);
        requestBody.put(inputField, inputValue);
        if (sourceId != null && !sourceId.isBlank()) {
            requestBody.put("source_id", sourceId);
        }
        if (includeVisuals != null) {
            requestBody.put("include_visuals", includeVisuals);
        }

        HttpHeaders headers = jsonHeaders();
        headers.set("X-Request-ID", "req_" + System.currentTimeMillis());
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    String.class
            );

            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new RuntimeException("算法服务返回错误: " + response.getStatusCode());
            }
            return objectMapper.readValue(response.getBody(), InferenceResponse.class);
        } catch (Exception e) {
            log.error("调用算法服务失败: {}", e.getMessage());
            throw new RuntimeException("算法服务调用失败: " + e.getMessage());
        }
    }

    public Map<String, Object> getOwnerGestureLibrary() {
        return requestOwnerGesture("", HttpMethod.GET, null, "获取手势库失败");
    }

    public Map<String, Object> activateOwnerGestureAlgorithm() {
        return requestOwnerGesture(
                "/algorithm",
                HttpMethod.PUT,
                Map.of("algorithm", OWNER_GESTURE_ALGORITHM),
                "启用 DINOv2 手势算法失败"
        );
    }

    public Map<String, Object> enrollOwnerGesture(Map<String, Object> requestBody) {
        return requestOwnerGesture("/enroll", HttpMethod.POST, requestBody, "录入手势失败");
    }

    public Map<String, Object> updateOwnerGesture(String prototypeId, Map<String, Object> requestBody) {
        return requestOwnerGesture("/" + prototypeId, HttpMethod.PUT, requestBody, "编辑手势失败");
    }

    public Map<String, Object> deleteOwnerGesture(String prototypeId) {
        return requestOwnerGesture("/" + prototypeId, HttpMethod.DELETE, null, "删除手势失败");
    }

    public Map<String, Object> getOwnerGestureState() {
        return requestOwnerGesture("/state", HttpMethod.GET, null, "获取手势状态失败");
    }

    public Map<String, Object> getOwnerGestureConfig() {
        return requestOwnerGesture("/config", HttpMethod.GET, null, "获取手势参数失败");
    }

    public Map<String, Object> patchOwnerGestureConfig(Map<String, Object> requestBody) {
        return requestOwnerGesture("/config", HttpMethod.PATCH, requestBody, "更新手势参数失败");
    }

    public Map<String, Object> putOwnerGestureConfig(Map<String, Object> requestBody) {
        return requestOwnerGesture("/config", HttpMethod.PUT, requestBody, "替换手势参数失败");
    }

    public Map<String, Object> getOwnerGesturePrototypes() {
        return requestOwnerGesture("/prototypes", HttpMethod.GET, null, "获取手势原型库失败");
    }

    public Map<String, Object> clearOwnerGesturePrototypes() {
        return requestOwnerGesture("/prototypes", HttpMethod.DELETE, null, "清空手势原型库失败");
    }

    public Map<String, Object> deleteOwnerGesturePrototype(String prototypeId) {
        return requestOwnerGesture("/prototypes/" + prototypeId, HttpMethod.DELETE, null, "删除手势原型失败");
    }

    public Map<String, Object> startOwnerGestureRecording(Map<String, Object> requestBody) {
        return requestOwnerGesture("/recordings/start", HttpMethod.POST, requestBody, "开始手势录入失败");
    }

    public Map<String, Object> cancelOwnerGestureRecording() {
        return requestOwnerGesture("/recordings/cancel", HttpMethod.POST, Map.of(), "取消手势录入失败");
    }

    public Map<String, Object> recognizeOwnerGesture(Map<String, Object> requestBody) {
        return requestOwnerGesture("/recognize", HttpMethod.POST, requestBody, "手势识别失败");
    }

    public Map<String, Object> getOwnerGestureControlSettings() {
        return requestOwnerGesture("/control-settings", HttpMethod.GET, null, "获取手势控制设置失败");
    }

    public Map<String, Object> saveOwnerGestureControlSettings(Map<String, Object> requestBody) {
        return requestOwnerGesture("/control-settings", HttpMethod.POST, requestBody, "保存手势控制设置失败");
    }

    private Map<String, Object> requestOwnerGesture(
            String path,
            HttpMethod method,
            Map<String, Object> requestBody,
            String errorPrefix
    ) {
        String url = gestureAlgorithmBaseUrl + "/api/v1/owner-gestures" + path;
        HttpHeaders headers = jsonHeaders();
        headers.set("X-Request-ID", "req_" + System.currentTimeMillis());
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<String> response = restTemplate.exchange(url, method, entity, String.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new RuntimeException("算法服务返回错误: " + response.getStatusCode());
            }
            return parseAlgorithmPayload(response.getBody());
        } catch (HttpStatusCodeException e) {
            log.error("{}: {}", errorPrefix, e.getMessage());
            throw toAlgorithmException(errorPrefix, e);
        } catch (Exception e) {
            log.error("{}: {}", errorPrefix, e.getMessage());
            throw new RuntimeException(errorPrefix + ": " + e.getMessage());
        }
    }

    private HttpHeaders jsonHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }

    private String resolveInferenceBaseUrl(String taskType) {
        if ("license_plate".equals(taskType)) {
            return licenseAlgorithmBaseUrl;
        }
        if ("police_gesture".equals(taskType)) {
            return policeAlgorithmBaseUrl;
        }
        if ("vehicle_type".equals(taskType)) {
            return vehicleAlgorithmBaseUrl;
        }
        throw new IllegalArgumentException("不支持的图片推理任务类型: " + taskType);
    }

    private Map<String, Object> parseAlgorithmPayload(String body) throws Exception {
        Map<String, Object> envelope = objectMapper.readValue(
                body,
                new TypeReference<Map<String, Object>>() {}
        );
        Object data = envelope.get("data");
        if (data instanceof Map<?, ?> dataMap) {
            Map<String, Object> typed = new LinkedHashMap<>();
            dataMap.forEach((key, value) -> typed.put(String.valueOf(key), value));
            return typed;
        }
        return envelope;
    }

    private RuntimeException toAlgorithmException(String prefix, HttpStatusCodeException e) {
        String message = extractAlgorithmError(e.getResponseBodyAsString(), e.getMessage());
        if (e.getStatusCode().is4xxClientError()) {
            return new IllegalArgumentException(prefix + ": " + message);
        }
        return new RuntimeException(prefix + ": " + message);
    }

    private String extractAlgorithmError(String body, String fallback) {
        if (body == null || body.isBlank()) {
            return fallback;
        }
        try {
            Map<String, Object> envelope = objectMapper.readValue(
                    body,
                    new TypeReference<Map<String, Object>>() {}
            );
            Object detail = envelope.get("detail");
            if (detail != null) {
                return String.valueOf(detail);
            }
            Object message = envelope.get("message");
            if (message != null) {
                return String.valueOf(message);
            }
        } catch (Exception ignored) {
            return body;
        }
        return fallback;
    }
}
