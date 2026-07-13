package com.visiondrive.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.agent.RecognitionFailureAgent;
import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.entity.Job;
import com.visiondrive.service.JobService;
import com.visiondrive.service.SystemLogService;
import com.visiondrive.websocket.AlertWebSocketHandler;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

@Slf4j
@RestController
@RequestMapping("/internal/api/v1/algorithm")
@RequiredArgsConstructor
@Tag(name = "算法回调", description = "接收算法服务回传的实时结果")
public class AlgorithmCallbackController {

    private final JobService jobService;
    private final AlertWebSocketHandler webSocketHandler;
    private final ObjectMapper objectMapper;
    private final SystemLogService systemLogService;
    private final RecognitionFailureAgent recognitionFailureAgent;

    @Operation(summary = "接收算法回调")
    @PostMapping("/events")
    public ApiResponse<Map<String, String>> receiveEvent(@RequestBody Map<String, Object> event) {
        log.info("收到算法回调: {}", event);

        String jobId = (String) event.get("jobId");
        String eventType = (String) event.get("eventType");

        // 1. 判断事件类型
        if ("progress".equals(eventType)) {
            // 进度更新
            Map<String, Object> data = (Map<String, Object>) event.get("data");
            Integer progress = (Integer) data.get("progress");
            Integer processedFrames = (Integer) data.get("processedFrames");
            Integer totalFrames = (Integer) data.get("totalFrames");

            jobService.updateJobStatus(jobId, "processing", progress,
                    processedFrames, totalFrames, null, null);

            // 推送进度给前端
            Map<String, Object> pushData = new HashMap<>();
            pushData.put("type", "job_progress");
            pushData.put("jobId", jobId);
            pushData.put("progress", progress);
            pushData.put("processedFrames", processedFrames);
            pushData.put("totalFrames", totalFrames);
            webSocketHandler.pushAlertToAllClients(pushData);

        } else if ("completed".equals(eventType)) {
            // 任务完成
            Map<String, Object> data = (Map<String, Object>) event.get("data");
            String resultUrl = (String) data.get("resultUrl");
            // 从 data 中取 totalFrames，用于更新 totalFrames 字段（可选）
            // 注意：如果之前 progress 回调里没有 totalFrames，这里可以补上
            // 但需要判断 data 中是否有 totalFrames，有则取，无则忽略
            Integer totalFrames = null;
            if (data.containsKey("totalFrames")) {
                totalFrames = (Integer) data.get("totalFrames");
            }
            // 调用 jobService 的 updateJobStatus 不需要传 totalFrames 时置 null 即可
            jobService.updateJobStatus(jobId, "completed", 100, null, totalFrames, resultUrl, null);
            Job job = jobService.getJob(jobId);
            Double confidence = extractConfidence(data);
            boolean reviewQueued = recognitionFailureAgent.submitIfNeeded(
                    job.getTaskType(), job.getInputUrl(), confidence, null, jobId
            );
            Map<String, Object> detail = callbackDetail(jobId, eventType, data);
            addEvidence(detail, job, confidence, reviewQueued);
            systemLogService.info("algorithm_callback", "job_completed", detail);

            // 推送完成消息给前端
            Map<String, Object> pushData = new HashMap<>();
            pushData.put("type", "job_completed");
            pushData.put("jobId", jobId);
            pushData.put("resultUrl", resultUrl);
            webSocketHandler.pushAlertToAllClients(pushData);

        } else if ("failed".equals(eventType)) {
            // 任务失败
            Map<String, Object> data = (Map<String, Object>) event.get("data");
            String errorMessage = (String) data.get("errorMessage");
            jobService.updateJobStatus(jobId, "failed", null, null, null, null, errorMessage);
            Job job = jobService.getJob(jobId);
            Double confidence = extractConfidence(data);
            boolean reviewQueued = recognitionFailureAgent.submitIfNeeded(
                    job.getTaskType(), job.getInputUrl(), confidence, errorMessage, jobId
            );
            Map<String, Object> detail = callbackDetail(jobId, eventType, data);
            detail.put("errorMessage", Objects.toString(errorMessage, ""));
            addEvidence(detail, job, confidence, reviewQueued);
            systemLogService.error("algorithm_callback", "job_failed", detail);

            // 推送失败消息
            Map<String, Object> pushData = new HashMap<>();
            pushData.put("type", "job_failed");
            pushData.put("jobId", jobId);
            pushData.put("errorMessage", errorMessage);
            webSocketHandler.pushAlertToAllClients(pushData);

        } else {
            log.warn("未知事件类型: {}", eventType);
            systemLogService.warn("algorithm_callback", "unknown_event", Map.of(
                    "jobId", Objects.toString(jobId, ""),
                    "eventType", Objects.toString(eventType, "")
            ));
        }

        Map<String, String> response = new HashMap<>();
        response.put("status", "received");
        return ApiResponse.success(response);
    }

    private Map<String, Object> callbackDetail(String jobId, String eventType, Map<String, Object> data) {
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("jobId", Objects.toString(jobId, ""));
        detail.put("eventType", Objects.toString(eventType, ""));
        if (data != null) {
            detail.put("progress", data.get("progress"));
            detail.put("processedFrames", data.get("processedFrames"));
            detail.put("totalFrames", data.get("totalFrames"));
            detail.put("resultUrl", Objects.toString(data.get("resultUrl"), ""));
        }
        return detail;
    }

    private void addEvidence(Map<String, Object> detail, Job job, Double confidence, boolean reviewQueued) {
        detail.put("taskType", job.getTaskType());
        detail.put("evidenceUrl", job.getInputUrl());
        detail.put("mediaType", "video");
        detail.put("confidence", confidence == null ? 0 : confidence);
        detail.put("agentReviewQueued", reviewQueued);
    }

    private Double extractConfidence(Map<String, Object> data) {
        if (data == null) return null;
        for (String key : new String[]{"confidence", "avgConfidence", "averageConfidence"}) {
            Object value = data.get(key);
            if (value instanceof Number number) return number.doubleValue();
        }
        Object results = data.get("results");
        if (results instanceof java.util.List<?> list) {
            return list.stream()
                    .filter(Map.class::isInstance)
                    .map(Map.class::cast)
                    .map(item -> item.get("confidence"))
                    .filter(Number.class::isInstance)
                    .map(Number.class::cast)
                    .mapToDouble(Number::doubleValue)
                    .average()
                    .stream()
                    .boxed()
                    .findFirst()
                    .orElse(null);
        }
        return null;
    }
}
