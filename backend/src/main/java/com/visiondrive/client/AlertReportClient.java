package com.visiondrive.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 调用独立 alert-service。邮件收件人和 SMTP 均由微服务管理，主后端只负责上报告警。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AlertReportClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${alert.report.enabled:true}")
    private boolean enabled;

    @Value("${alert.report.base-url:http://localhost:8096}")
    private String baseUrl;

    @Value("${alert.report.token:}")
    private String token;

    public boolean report(Map<String, Object> alert) {
        if (!enabled) {
            log.debug("告警微服务上报已关闭: alertId={}", alert.get("alertId"));
            return false;
        }
        if (token == null || token.isBlank()) {
            log.warn("未配置 ALERT_SERVICE_TOKEN，跳过告警微服务上报: alertId={}", alert.get("alertId"));
            return false;
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Alert-Token", token);

        ResponseEntity<Map> response = restTemplate.exchange(
                endpoint(),
                HttpMethod.POST,
                new HttpEntity<>(buildRequest(alert), headers),
                Map.class
        );
        Object code = response.getBody() == null ? null : response.getBody().get("code");
        if (!response.getStatusCode().is2xxSuccessful() || !"200".equals(Objects.toString(code, ""))) {
            throw new IllegalStateException("告警微服务返回异常: status=" + response.getStatusCode()
                    + ", body=" + response.getBody());
        }

        log.info("告警已上报邮件微服务: alertId={}, severity={}",
                alert.get("alertId"), alert.get("severity"));
        return true;
    }

    private Map<String, Object> buildRequest(Map<String, Object> alert) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("alertId", Objects.toString(alert.get("alertId"), ""));
        body.put("severity", Objects.toString(alert.get("severity"), "").toLowerCase());
        body.put("title", Objects.toString(alert.get("title"), "系统告警"));
        body.put("summary", Objects.toString(alert.get("summary"), ""));
        body.put("anomalyType", Objects.toString(alert.get("anomalyType"), "UNKNOWN"));
        body.put("affectedModule", Objects.toString(alert.get("affectedModule"), "unknown"));
        body.put("occurredAt", Objects.toString(alert.get("occurredAt"), ""));
        body.put("metrics", parseMetrics(alert.get("metrics")));
        body.put("suggestedActions", parseActions(alert.get("suggestedActions")));
        return body;
    }

    private Map<String, String> parseMetrics(Object raw) {
        Map<String, String> metrics = new LinkedHashMap<>();
        if (raw instanceof Map<?, ?> map) {
            map.forEach((key, value) -> metrics.put(Objects.toString(key, ""), Objects.toString(value, "")));
            return metrics;
        }
        String text = Objects.toString(raw, "").trim();
        if (text.isBlank()) {
            return metrics;
        }
        try {
            JsonNode root = objectMapper.readTree(text);
            if (root.isObject()) {
                root.fields().forEachRemaining(entry -> metrics.put(
                        entry.getKey(),
                        entry.getValue().isTextual() ? entry.getValue().asText() : entry.getValue().toString()
                ));
            }
        } catch (Exception ignored) {
            metrics.put("detail", text);
        }
        return metrics;
    }

    private List<String> parseActions(Object raw) {
        if (raw instanceof List<?> list) {
            return list.stream().map(value -> Objects.toString(value, "")).filter(value -> !value.isBlank()).toList();
        }
        String text = Objects.toString(raw, "").trim();
        if (text.isBlank()) {
            return List.of();
        }
        List<String> actions = new ArrayList<>();
        for (String line : text.split("[\\r\\n]+")) {
            String action = line.replaceFirst("^\\s*\\d+[.、)]\\s*", "").trim();
            if (!action.isBlank()) {
                actions.add(action);
            }
        }
        return actions;
    }

    private String endpoint() {
        String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        return normalized + "/api/alert/receive";
    }
}
