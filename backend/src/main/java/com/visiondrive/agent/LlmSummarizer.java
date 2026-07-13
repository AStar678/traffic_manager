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

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Component
@RequiredArgsConstructor
public class LlmSummarizer {

    private final RestTemplate restTemplate;
    private final SystemLogService systemLogService;

    @Value("${llm.api-key:}")
    private String apiKey;

    @Value("${llm.model:qwen-plus}")
    private String model;

    @Value("${llm.base-url:https://dashscope.aliyuncs.com/compatible-mode/v1}")
    private String baseUrl;

    /**
     * 生成告警摘要。配置 LLM_API_KEY 后优先调用 LLM，失败时回退到本地模板。
     */
    public Map<String, Object> generateSummary(AnomalyEvent event) {
        Map<String, Object> summary = generateTemplateSummary(event);
        if (event.getType() == AnomalyType.RECOGNITION_FAILURE_REVIEW) {
            // 这类告警的 summary 已经是千问视觉模型对失败图像/视频的复核结论。
            // 不再二次调用文字模型，避免邮件中的失败原因被泛化或改写。
            return summary;
        }
        String llmAnalysis = generateLlmAnalysis(event);
        if (llmAnalysis != null && !llmAnalysis.isBlank()) {
            summary.put("llmAnalysis", llmAnalysis);
            summary.put("summary", llmAnalysis);
        }
        return summary;
    }

    private Map<String, Object> generateTemplateSummary(AnomalyEvent event) {
        Map<String, Object> summary = new HashMap<>();

        // 生成告警ID
        String alertId = "alert_" + System.currentTimeMillis();

        // 构建结构化告警
        summary.put("alertId", alertId);
        summary.put("severity", event.getSeverity().name().toLowerCase());
        summary.put("severityLabel", event.getSeverity().getLabel());
        summary.put("severityEmoji", event.getSeverity().getEmoji());
        summary.put("title", event.getTitle());
        summary.put("summary", event.getSummary());
        summary.put("anomalyType", event.getType().name());
        summary.put("affectedModule", event.getAffectedModule());
        summary.put("metrics", event.getMetrics());
        summary.put("suggestedActions", event.getSuggestedActions());
        summary.put("occurredAt", LocalDateTime.now().format(DateTimeFormatter.ISO_DATE_TIME));

        // 如果是 LLM Token 相关，追加详细信息
        if (event.getType() == AnomalyType.LLM_TOKEN_EXCEEDED) {
            summary.put("llmSuggestion", "建议优化 Prompt 设计，减少 Token 消耗");
        }

        // 如果是系统资源相关
        if (event.getType() == AnomalyType.SYSTEM_RESOURCE_HIGH) {
            summary.put("resourceSuggestion", "建议检查是否有内存泄漏或请求积压");
        }

        log.info("生成告警摘要: {}", summary.get("title"));
        return summary;
    }

    /**
     * 实际调用 LLM API 生成摘要
     */
    public Map<String, Object> generateSummaryWithLLM(AnomalyEvent event) {
        return generateSummary(event);
    }

    private String generateLlmAnalysis(AnomalyEvent event) {
        if (apiKey == null || apiKey.isBlank()) {
            return "";
        }

        long startTime = System.currentTimeMillis();
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("anomalyType", event.getType().name());
        detail.put("model", model);

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);

            Map<String, Object> requestBody = new LinkedHashMap<>();
            requestBody.put("model", model);
            requestBody.put("temperature", 0.2);
            requestBody.put("messages", List.of(
                    Map.of("role", "system", "content", "你是 VisionDrive 车载视觉系统的告警智能体。请用中文输出一段简洁、准确、可执行的告警摘要，不要使用 Markdown 标题。"),
                    Map.of("role", "user", "content", buildPrompt(event))
            ));

            ResponseEntity<Map> response = restTemplate.exchange(
                    llmEndpoint(),
                    HttpMethod.POST,
                    new HttpEntity<>(requestBody, headers),
                    Map.class
            );

            Map<?, ?> responseBody = response.getBody();
            String content = extractContent(responseBody);
            long totalTokens = extractTotalTokens(responseBody);

            detail.put("latencyMs", System.currentTimeMillis() - startTime);
            detail.put("tokens", totalTokens);
            systemLogService.info("llm", "token_usage", detail);
            return content;
        } catch (ResourceAccessException e) {
            detail.put("latencyMs", System.currentTimeMillis() - startTime);
            detail.put("errorMessage", Objects.toString(e.getMessage(), ""));
            systemLogService.warn("llm", "timeout", detail);
            log.warn("LLM 告警摘要生成超时，使用本地模板: {}", e.getMessage());
        } catch (Exception e) {
            detail.put("latencyMs", System.currentTimeMillis() - startTime);
            detail.put("errorMessage", Objects.toString(e.getMessage(), ""));
            systemLogService.warn("llm", "failure", detail);
            log.warn("LLM 告警摘要生成失败，使用本地模板: {}", e.getMessage());
        }
        return "";
    }

    private String buildPrompt(AnomalyEvent event) {
        return String.format("""
                你是一个系统运维专家。请分析以下异常事件并生成告警摘要：
                
                异常类型: %s
                异常描述: %s
                影响模块: %s
                指标数据: %s
                建议措施: %s
                
                请用一段自然语言概括异常类型、发生时间、影响范围、可能根因和最优先处置措施，控制在180字以内。
                """,
                event.getType().name(),
                event.getSummary(),
                event.getAffectedModule(),
                event.getMetrics(),
                event.getSuggestedActions()
        );
    }

    private String llmEndpoint() {
        String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        return normalized + "/chat/completions";
    }

    private String extractContent(Map<?, ?> responseBody) {
        if (responseBody == null) {
            return "";
        }
        Object choices = responseBody.get("choices");
        if (choices instanceof List<?> choiceList && !choiceList.isEmpty() && choiceList.get(0) instanceof Map<?, ?> choice) {
            Object message = choice.get("message");
            if (message instanceof Map<?, ?> messageMap) {
                return Objects.toString(messageMap.get("content"), "");
            }
            return Objects.toString(choice.get("text"), "");
        }
        return "";
    }

    private long extractTotalTokens(Map<?, ?> responseBody) {
        if (responseBody == null || !(responseBody.get("usage") instanceof Map<?, ?> usage)) {
            return 0;
        }
        Object totalTokens = usage.get("total_tokens");
        if (totalTokens instanceof Number number) {
            return number.longValue();
        }
        try {
            return Long.parseLong(Objects.toString(totalTokens, "0"));
        } catch (NumberFormatException e) {
            return 0;
        }
    }
}
