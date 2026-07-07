package com.visiondrive.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.InferenceResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class AlgorithmClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${algorithm.base-url:http://localhost:8000}")
    private String algorithmBaseUrl;

    @Value("${algorithm.inference.image:/api/v1/inference/image}")
    private String inferencePath;

    /**
     * 调用算法服务进行图片识别
     */
    public InferenceResponse callImageInference(String taskType, String imageUrl) {
        log.info("调用算法服务: taskType={}, imageUrl={}", taskType, imageUrl);

        String url = algorithmBaseUrl + inferencePath;

        // 构造请求体
        Map<String, String> requestBody = new HashMap<>();
        requestBody.put("task_type", taskType);
        requestBody.put("image_url", imageUrl);

        // 设置请求头
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Request-ID", "req_" + System.currentTimeMillis());

        HttpEntity<Map<String, String>> entity = new HttpEntity<>(requestBody, headers);

        try {
            // 发送请求
            ResponseEntity<String> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    String.class
            );

            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new RuntimeException("算法服务返回错误: " + response.getStatusCode());
            }

            // 解析响应
            return objectMapper.readValue(response.getBody(), InferenceResponse.class);

        } catch (Exception e) {
            log.error("调用算法服务失败: {}", e.getMessage());
            throw new RuntimeException("算法服务调用失败: " + e.getMessage());
        }
    }
}