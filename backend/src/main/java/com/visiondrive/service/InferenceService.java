package com.visiondrive.service;

import com.visiondrive.agent.RecognitionFailureAgent;
import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.model.dto.InferenceRequest;
import com.visiondrive.model.dto.InferenceResponse;
import com.visiondrive.model.dto.CameraSlotResponse;
import com.visiondrive.model.dto.MultiCameraInferenceResponse;
import com.visiondrive.common.utils.JsonLogBuilder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
@Service
@RequiredArgsConstructor
public class InferenceService {

    private final AlgorithmClient algorithmClient;
    private final RecognitionHistoryService recognitionHistoryService;
    private final SystemLogService systemLogService;
    private final CameraManagerService cameraManagerService;
    private final RecognitionFailureAgent recognitionFailureAgent;
    private final ExecutorService multiCameraExecutor = Executors.newFixedThreadPool(6);
    private final ExecutorService persistenceExecutor = Executors.newFixedThreadPool(2);
    private final Map<String, Long> lastCameraPersistenceAt = new ConcurrentHashMap<>();
    private static final long CAMERA_PERSISTENCE_INTERVAL_MS = 5_000;

    @PreDestroy
    public void shutdownInferenceExecutor() {
        multiCameraExecutor.shutdownNow();
        persistenceExecutor.shutdownNow();
    }

    /**
     * 处理图片推理
     */
    public InferenceResponse processImageInference(InferenceRequest request, Long userId) {
        long startTime = System.currentTimeMillis();
        String traceId = JsonLogBuilder.generateTraceId();

        log.info("开始推理: traceId={}, taskType={}, imageUrl={}",
                traceId, request.getTaskType(), request.getImageUrl());

        try {
        // 调用算法客户端
        InferenceResponse response = algorithmClient.callImageInference(
                request.getTaskType(),
                request.getImageUrl()
        );

            // 2. 保存识别记录到数据库
            recognitionHistoryService.saveInference(userId, request, response, traceId,
                    System.currentTimeMillis() - startTime, true, null);

            recordInferenceSystemLog(request, response, traceId,
                    System.currentTimeMillis() - startTime, null, userId);

            log.info("推理完成: traceId={}, detectionCount={}, latency={}ms",
                    traceId,
                    response.getData() != null ? response.getData().getDetectionCount() : 0,
                    System.currentTimeMillis() - startTime);

            return response;

        } catch (Exception e) {
            log.error("推理失败: traceId={}, error={}", traceId, e.getMessage());
            // 保存失败记录
            recognitionHistoryService.saveInference(userId, request, null, traceId,
                    System.currentTimeMillis() - startTime, false, e.getMessage());
            recordInferenceSystemLog(request, null, traceId,
                    System.currentTimeMillis() - startTime, e.getMessage(), userId);
            throw new RuntimeException("推理失败: " + e.getMessage());
        }
    }

    /**
     * 对三个摄像头槽位并发取帧和推理。帧文件以本地绝对路径传给算法进程，不传输图像字节。
     */
    public MultiCameraInferenceResponse processCameraInference(String taskType, Long userId) {
        return processCameraInference(taskType, false, userId);
    }

    public MultiCameraInferenceResponse processCameraInference(String taskType, boolean includeVisuals, Long userId) {
        if (!"license_plate".equals(taskType)
                && !"police_gesture".equals(taskType)
                && !"vehicle_type".equals(taskType)) {
            throw new IllegalArgumentException("三路摄像头推理仅支持 license_plate、vehicle_type 和 police_gesture");
        }

        long started = System.currentTimeMillis();
        List<CompletableFuture<MultiCameraInferenceResponse.CameraInferenceResult>> futures = cameraManagerService.listSlots()
                .stream()
                .map(slot -> CompletableFuture.supplyAsync(
                        () -> inferCameraSlot(taskType, slot, includeVisuals, userId),
                        multiCameraExecutor
                ))
                .toList();

        List<MultiCameraInferenceResponse.CameraInferenceResult> cameraResults = futures.stream()
                .map(CompletableFuture::join)
                .toList();

        List<InferenceResponse.Detection> detections = cameraResults.stream()
                .filter(result -> result.getResult() != null && result.getResult().getDetections() != null)
                .flatMap(result -> result.getResult().getDetections().stream())
                .toList();

        MultiCameraInferenceResponse response = new MultiCameraInferenceResponse();
        response.setTaskType(taskType);
        response.setLatencyMs(System.currentTimeMillis() - started);
        response.setCameras(cameraResults);
        response.setDetections(detections);
        response.setDetectionCount(detections.size());
        response.setServerTimeMs(System.currentTimeMillis());
        return response;
    }

    private MultiCameraInferenceResponse.CameraInferenceResult inferCameraSlot(
            String taskType,
            CameraSlotResponse slot,
            boolean includeVisuals,
            Long userId
    ) {
        MultiCameraInferenceResponse.CameraInferenceResult result = new MultiCameraInferenceResponse.CameraInferenceResult();
        result.setSlotId(slot.getSlotId());
        result.setCameraName(slot.getName());
        result.setSourceType(slot.getSourceType());
        result.setFrameUrl(slot.getFrameUrl());

        if ("OFF".equals(slot.getSourceType())) {
            result.setStatus("off");
            return result;
        }

        long started = System.currentTimeMillis();
        String traceId = JsonLogBuilder.generateTraceId();
        InferenceRequest recordRequest = new InferenceRequest();
        recordRequest.setTaskType(taskType);

        try {
            CameraManagerService.CameraFrame frame = cameraManagerService.captureSlot(slot.getSlotId());
            result.setFrameId(frame.frameId());
            result.setFramePts(frame.framePts());
            result.setFrameTimeBase(frame.frameTimeBase());
            result.setFrameCapturedAtMs(frame.frameCapturedAtMs());
            recordRequest.setImageUrl(frame.path().toString());
            InferenceResponse inference = algorithmClient.callFileInference(
                    taskType,
                    frame.path().toString(),
                    "camera-slot-" + slot.getSlotId(),
                    includeVisuals
            );
            InferenceResponse.InferenceData data = inference.getData();
            if (data != null && data.getDetections() != null) {
                data.getDetections().forEach(detection -> {
                    detection.setCameraSlotId(slot.getSlotId());
                    detection.setCameraName(slot.getName());
                    detection.setFrameId(frame.frameId());
                    detection.setFramePts(frame.framePts());
                    detection.setFrameTimeBase(frame.frameTimeBase());
                    detection.setFrameCapturedAtMs(frame.frameCapturedAtMs());
                });
            }
            result.setResult(data);
            result.setStatus("ready");
            persistCameraInferenceAsync(
                    taskType,
                    slot.getSlotId(),
                    recordRequest,
                    inference,
                    traceId,
                    System.currentTimeMillis() - started,
                    true,
                    null,
                    userId
            );
        } catch (Exception error) {
            result.setStatus("error");
            result.setError(error.getMessage());
            if (recordRequest.getImageUrl() == null) recordRequest.setImageUrl(slot.getPath());
            persistCameraInferenceAsync(
                    taskType,
                    slot.getSlotId(),
                    recordRequest,
                    null,
                    traceId,
                    System.currentTimeMillis() - started,
                    false,
                    error.getMessage(),
                    userId
            );
            log.warn("摄像头 {} 推理失败: {}", slot.getSlotId(), error.getMessage());
        }
        return result;
    }

    private void persistCameraInferenceAsync(
            String taskType,
            int slotId,
            InferenceRequest request,
            InferenceResponse response,
            String traceId,
            long latencyMs,
            boolean success,
            String errorMessage,
            Long userId
    ) {
        String key = userId + ":" + taskType + ":" + slotId;
        long now = System.currentTimeMillis();
        AtomicBoolean accepted = new AtomicBoolean(false);
        lastCameraPersistenceAt.compute(key, (ignored, previous) -> {
            if (previous == null || now - previous >= CAMERA_PERSISTENCE_INTERVAL_MS) {
                accepted.set(true);
                return now;
            }
            return previous;
        });
        if (!accepted.get()) return;

        CompletableFuture.runAsync(() -> {
            recognitionHistoryService.saveInference(
                    userId, request, response, traceId, latencyMs, success, errorMessage
            );
            recordInferenceSystemLog(request, response, traceId, latencyMs, errorMessage, userId);
        }, persistenceExecutor).exceptionally(error -> {
            log.warn("异步保存摄像头推理记录失败: taskType={}, slotId={}, error={}",
                    taskType, slotId, error.getMessage());
            return null;
        });
    }

    private void recordInferenceSystemLog(
            InferenceRequest request,
            InferenceResponse response,
            String traceId,
            long latencyMs,
            String errorMessage,
            Long userId
    ) {
        String taskType = request.getTaskType();
        String module = resolveMonitorModule(taskType);
        int detectionCount = response != null && response.getData() != null && response.getData().getDetectionCount() != null
                ? response.getData().getDetectionCount()
                : 0;
        boolean success = errorMessage == null && detectionCount > 0;
        double confidence = averageConfidence(response);
        String reviewFailureReason = errorMessage;
        if (reviewFailureReason == null && detectionCount == 0) {
            reviewFailureReason = "算法未检测到目标";
        }
        boolean reviewQueued = recognitionFailureAgent.submitIfNeeded(
                taskType,
                request.getImageUrl(),
                confidence,
                reviewFailureReason,
                traceId
        );

        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("traceId", traceId);
        detail.put("taskType", taskType);
        detail.put("inputType", "image");
        detail.put("imageUrl", request.getImageUrl());
        detail.put("evidenceUrl", request.getImageUrl());
        detail.put("mediaType", "image");
        detail.put("latencyMs", latencyMs);
        detail.put("detectionCount", detectionCount);
        detail.put("confidence", confidence);
        detail.put("agentReviewQueued", reviewQueued);
        if (errorMessage != null) {
            detail.put("errorMessage", errorMessage);
        }

        if (!success) {
            systemLogService.record("ERROR", module, "failure", JsonLogBuilder.toJson(detail), userId, traceId);
        } else if (recognitionFailureAgent.isReviewRequired(taskType, confidence, null)) {
            systemLogService.record("WARN", module, "low_confidence", JsonLogBuilder.toJson(detail), userId, traceId);
        } else {
            systemLogService.record("INFO", module, "success", JsonLogBuilder.toJson(detail), userId, traceId);
        }
    }

    private double averageConfidence(InferenceResponse response) {
        if (response == null || response.getData() == null || response.getData().getDetections() == null) {
            return 0.0;
        }
        return response.getData().getDetections().stream()
                .map(InferenceResponse.Detection::getConfidence)
                .filter(value -> value != null && value > 0)
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0.0);
    }

    private String resolveMonitorModule(String taskType) {
        if ("license_plate".equals(taskType)) {
            return "license_plate";
        }
        if ("police_gesture".equals(taskType)) {
            return "police_gesture";
        }
        if ("owner_gesture".equals(taskType)) {
            return "owner_gesture";
        }
        if ("vehicle_type".equals(taskType)) {
            return "vehicle_type";
        }
        return taskType != null && taskType.contains("gesture") ? "gesture" : "inference";
    }
}
