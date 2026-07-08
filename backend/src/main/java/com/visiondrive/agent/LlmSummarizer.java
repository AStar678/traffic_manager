package com.visiondrive.agent;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class LlmSummarizer {

    /**
     * 生成告警摘要（模拟 LLM 调用，实际可接入 DeepSeek API）
     */
    public Map<String, Object> generateSummary(AnomalyEvent event) {
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
     * 实际调用 LLM API 生成摘要（后续接入 DeepSeek）
     */
    public Map<String, Object> generateSummaryWithLLM(AnomalyEvent event) {
        // 先使用模板生成
        Map<String, Object> summary = generateSummary(event);

        // TODO: 实际调用 LLM API
        // 示例：
        // String prompt = buildPrompt(event);
        // String llmResponse = deepSeekClient.call(prompt);
        // summary.put("llmAnalysis", llmResponse);

        return summary;
    }

    private String buildPrompt(AnomalyEvent event) {
        return String.format("""
                你是一个系统运维专家。请分析以下异常事件并生成告警摘要：
                
                异常类型: %s
                异常描述: %s
                影响模块: %s
                指标数据: %s
                建议措施: %s
                
                请生成一个结构化的告警摘要。
                """,
                event.getType().name(),
                event.getSummary(),
                event.getAffectedModule(),
                event.getMetrics(),
                event.getSuggestedActions()
        );
    }
}