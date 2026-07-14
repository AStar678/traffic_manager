package com.visiondrive.agent;

import com.visiondrive.common.utils.JsonLogBuilder;
import com.visiondrive.service.SystemLogService;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 将低置信度或失败的车牌/交警手势样本异步交给千问视觉模型复核。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RecognitionFailureAgent {

    private final QwenVisionReviewer visionReviewer;
    private final SystemLogService systemLogService;
    private final AlertDispatcher alertDispatcher;
    private final ExecutorService reviewExecutor = Executors.newSingleThreadExecutor();
    private final Map<String, Long> lastSubmittedAt = new ConcurrentHashMap<>();

    @Value("${alert.agent.recognition-review-enabled:true}")
    private boolean enabled;

    @Value("${alert.agent.low-confidence-threshold:0.5}")
    private double lowConfidenceThreshold;

    @Value("${alert.agent.recognition-review-cooldown:60000}")
    private long cooldownMs;

    public boolean isReviewRequired(String taskType, Double confidence, String failureReason) {
        if (!isSupportedTask(taskType)) return false;
        if (failureReason != null && !failureReason.isBlank()) return true;
        return confidence == null || confidence <= 0 || confidence < lowConfidenceThreshold;
    }

    public boolean submitIfNeeded(
            String taskType,
            String evidenceUrl,
            Double confidence,
            String failureReason,
            String traceId
    ) {
        if (!enabled || !visionReviewer.isConfigured()
                || !isReviewRequired(taskType, confidence, failureReason)) return false;
        if (evidenceUrl == null || evidenceUrl.isBlank()) {
            log.warn("识别失败样本缺少证据地址，无法提交 Agent: taskType={}, traceId={}", taskType, traceId);
            return false;
        }

        String key = taskType + ":" + evidenceUrl;
        long now = System.currentTimeMillis();
        Long previous = lastSubmittedAt.putIfAbsent(key, now);
        if (previous != null && now - previous < cooldownMs) {
            return false;
        }
        lastSubmittedAt.put(key, now);

        CompletableFuture.runAsync(
                () -> reviewAndDispatch(taskType, evidenceUrl, confidence, failureReason, traceId),
                reviewExecutor
        ).exceptionally(error -> {
            log.warn("失败样本 Agent 异步复核异常: taskType={}, error={}", taskType, error.getMessage());
            return null;
        });
        return true;
    }

    private void reviewAndDispatch(
            String taskType,
            String evidenceUrl,
            Double confidence,
            String failureReason,
            String traceId
    ) {
        String module = module(taskType);
        Map<String, Object> detail = baseDetail(taskType, evidenceUrl, confidence, failureReason);
        try {
            QwenVisionReviewer.ReviewResult result = visionReviewer.review(
                    taskType, evidenceUrl, confidence, failureReason
            );
            detail.put("agentReviewStatus", "completed");
            detail.put("agentModel", result.model());
            detail.put("agentAnalysis", result.analysis());
            detail.put("agentTokens", result.tokens());
            systemLogService.record("ERROR", module, "agent_review", JsonLogBuilder.toJson(detail), null, traceId);

            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.RECOGNITION_FAILURE_REVIEW);
            event.setAffectedModule(module);
            event.setSeverity(AlertSeverity.WARNING);
            event.setTitle("license_plate".equals(taskType) ? "车牌识别失败样本已完成 Agent 复核" : "交警手势失败样本已完成 Agent 复核");
            event.setSummary(result.analysis());
            event.setMetrics(JsonLogBuilder.toJson(Map.of(
                    "confidence", confidence == null ? 0 : confidence,
                    "evidenceUrl", evidenceUrl,
                    "agentModel", result.model(),
                    "agentAnalysis", result.analysis(),
                    "traceId", Objects.toString(traceId, "")
            )));
            event.setSuggestedActions("1. 在错误日志中回放失败样本\n2. 根据 Agent 根因建议调整输入或模型\n3. 将确认后的样本加入困难样本集");
            alertDispatcher.dispatch(event);
        } catch (Exception error) {
            detail.put("agentReviewStatus", "failed");
            detail.put("agentError", Objects.toString(error.getMessage(), ""));
            systemLogService.record("ERROR", module, "agent_review_failed", JsonLogBuilder.toJson(detail), null, traceId);
            log.warn("千问失败样本复核失败: taskType={}, evidenceUrl={}, error={}",
                    taskType, evidenceUrl, error.getMessage());
        }
    }

    private Map<String, Object> baseDetail(
            String taskType,
            String evidenceUrl,
            Double confidence,
            String failureReason
    ) {
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("taskType", taskType);
        detail.put("evidenceUrl", evidenceUrl);
        detail.put("mediaType", isVideo(evidenceUrl) ? "video" : "image");
        detail.put("confidence", confidence == null ? 0 : confidence);
        detail.put("failureReason", Objects.toString(failureReason, "低置信度"));
        return detail;
    }

    private boolean isSupportedTask(String taskType) {
        return "license_plate".equals(taskType) || "police_gesture".equals(taskType);
    }

    private String module(String taskType) {
        return "license_plate".equals(taskType) ? "license_plate" : "police_gesture";
    }

    private boolean isVideo(String url) {
        String normalized = url == null ? "" : url.toLowerCase();
        return normalized.matches(".*\\.(mp4|avi|mov|mkv|flv|wmv)(\\?.*)?$");
    }

    @PreDestroy
    public void shutdown() {
        reviewExecutor.shutdownNow();
    }
}
