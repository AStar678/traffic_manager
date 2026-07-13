package com.visiondrive.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.InferenceRequest;
import com.visiondrive.model.dto.InferenceResponse;
import com.visiondrive.model.entity.InferenceRecord;
import com.visiondrive.repository.InferenceRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Service
@RequiredArgsConstructor
public class RecognitionHistoryService {

    private static final String OWNER_GESTURE_SOURCE = "owner-gesture-camera";
    private static final int MAX_TARGET_LENGTH = 120;

    private final InferenceRecordRepository recordRepository;
    private final ObjectMapper objectMapper;

    public void saveInference(
            Long userId,
            InferenceRequest request,
            InferenceResponse response,
            String traceId,
            long latencyMs,
            boolean success,
            String errorMessage
    ) {
        Integer detectionCount = detectionCount(response);
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("target", success
                ? inferenceTarget(response, detectionCount)
                : failureTarget(errorMessage));
        Double confidence = averageConfidence(response);
        if (confidence != null) {
            summary.put("confidence", confidence);
        }

        saveRecord(
                userId,
                traceId,
                request.getTaskType(),
                "image",
                request.getImageUrl(),
                latencyMs,
                success,
                errorMessage,
                detectionCount,
                summary
        );
    }

    public void saveOwnerGesture(
            Long userId,
            Map<String, Object> result,
            String traceId,
            long latencyMs,
            boolean success,
            String errorMessage
    ) {
        Map<String, Object> safeResult = result == null ? Map.of() : result;
        boolean matched = success && booleanValue(safeResult, "matched", "recognized", true);
        String gestureName = firstString(safeResult, "gestureName", "gesture_name", "label", "name");
        if (gestureName.isBlank() && safeResult.get("recognition") instanceof Map<?, ?> recognition) {
            gestureName = firstString(recognition, "gestureName", "gesture_name", "label", "name");
        }

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("target", success
                ? truncate(matched && !gestureName.isBlank() ? gestureName : "未匹配到手势")
                : failureTarget(errorMessage));
        Double confidence = extractConfidence(safeResult);
        if (confidence != null) {
            summary.put("confidence", confidence);
        }

        saveRecord(
                userId,
                traceId,
                "owner_gesture",
                "camera",
                OWNER_GESTURE_SOURCE,
                latencyMs,
                success,
                errorMessage,
                matched ? 1 : 0,
                summary
        );
    }

    private void saveRecord(
            Long userId,
            String traceId,
            String taskType,
            String inputType,
            String inputUrl,
            long latencyMs,
            boolean success,
            String errorMessage,
            Integer detectionCount,
            Map<String, Object> summary
    ) {
        if (userId == null) {
            log.warn("跳过未绑定用户的识别历史: traceId={}, taskType={}", traceId, taskType);
            return;
        }

        try {
            InferenceRecord record = new InferenceRecord();
            record.setTraceId(traceId);
            record.setTaskType(taskType);
            record.setInputType(inputType);
            record.setInputUrl(inputUrl);
            record.setResultUrl(success ? inputUrl : null);
            record.setResultJson(objectMapper.writeValueAsString(summary));
            record.setDetectionCount(detectionCount);
            record.setLatencyMs(latencyMs);
            record.setSuccess(success);
            record.setErrorMessage(errorMessage);
            record.setUserId(userId);
            record.setCreatedAt(LocalDateTime.now());

            InferenceRecord saved = recordRepository.save(record);
            log.info("记录保存成功: recordId={}, userId={}, taskType={}", saved.getId(), userId, taskType);
        } catch (Exception error) {
            log.error("保存记录失败: traceId={}, userId={}, taskType={}, error={}",
                    traceId, userId, taskType, error.getMessage());
        }
    }

    private Integer detectionCount(InferenceResponse response) {
        if (response == null || response.getData() == null) {
            return 0;
        }
        if (response.getData().getDetectionCount() != null) {
            return response.getData().getDetectionCount();
        }
        List<InferenceResponse.Detection> detections = response.getData().getDetections();
        return detections == null ? 0 : detections.size();
    }

    private String inferenceTarget(InferenceResponse response, int detectionCount) {
        if (response == null || response.getData() == null || response.getData().getDetections() == null) {
            return detectionCount > 0 ? "检测到 " + detectionCount + " 个目标" : "未检测到目标";
        }

        String target = response.getData().getDetections().stream()
                .map(this::detectionLabel)
                .filter(label -> !label.isBlank())
                .distinct()
                .limit(3)
                .reduce((left, right) -> left + " / " + right)
                .orElse(detectionCount > 0 ? "检测到 " + detectionCount + " 个目标" : "未检测到目标");
        return truncate(target);
    }

    private String detectionLabel(InferenceResponse.Detection detection) {
        for (String value : List.of(
                Objects.toString(detection.getPlateNumber(), ""),
                Objects.toString(detection.getGestureName(), ""),
                Objects.toString(detection.getVehicleTypeName(), ""),
                Objects.toString(detection.getVehicleType(), ""),
                Objects.toString(detection.getDetectionClass(), ""),
                Objects.toString(detection.getObjectType(), "")
        )) {
            if (!value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private Double averageConfidence(InferenceResponse response) {
        if (response == null || response.getData() == null || response.getData().getDetections() == null) {
            return null;
        }
        return response.getData().getDetections().stream()
                .map(this::detectionConfidence)
                .filter(Objects::nonNull)
                .mapToDouble(Double::doubleValue)
                .average()
                .stream()
                .boxed()
                .findFirst()
                .orElse(null);
    }

    private Double detectionConfidence(InferenceResponse.Detection detection) {
        if (detection.getConfidence() != null) return detection.getConfidence();
        if (detection.getOcrConfidence() != null) return detection.getOcrConfidence();
        return detection.getDetectionConfidence();
    }

    private Double extractConfidence(Map<String, Object> result) {
        for (String key : List.of("confidence", "score", "similarity", "avgConfidence")) {
            Double parsed = toDouble(result.get(key));
            if (parsed != null) return parsed;
        }
        if (result.get("recognition") instanceof Map<?, ?> recognition) {
            for (String key : List.of("confidence", "score", "similarity")) {
                Double parsed = toDouble(recognition.get(key));
                if (parsed != null) return parsed;
            }
        }
        return null;
    }

    private boolean booleanValue(Map<String, Object> values, String firstKey, String secondKey, boolean fallback) {
        Object value = values.containsKey(firstKey) ? values.get(firstKey) : values.get(secondKey);
        if (value instanceof Boolean bool) return bool;
        if (value != null) return Boolean.parseBoolean(Objects.toString(value));
        return fallback;
    }

    private String firstString(Map<?, ?> values, String... keys) {
        for (String key : keys) {
            Object value = values.get(key);
            if (value != null && !Objects.toString(value, "").isBlank()) {
                return Objects.toString(value);
            }
        }
        return "";
    }

    private Double toDouble(Object value) {
        if (value instanceof Number number) return number.doubleValue();
        if (value == null) return null;
        try {
            return Double.parseDouble(Objects.toString(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String truncate(String value) {
        if (value == null || value.length() <= MAX_TARGET_LENGTH) return value;
        return value.substring(0, MAX_TARGET_LENGTH - 1) + "…";
    }

    private String failureTarget(String errorMessage) {
        return truncate(errorMessage == null || errorMessage.isBlank() ? "识别失败" : errorMessage);
    }
}
