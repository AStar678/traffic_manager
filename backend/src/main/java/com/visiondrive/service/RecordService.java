package com.visiondrive.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.RecognitionRecordResponse;
import com.visiondrive.model.entity.InferenceRecord;
import com.visiondrive.repository.InferenceRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class RecordService {

    private final InferenceRecordRepository recordRepository;

    private final ObjectMapper objectMapper;

    public Page<RecognitionRecordResponse> queryRecords(
            Long userId,
            String role,
            String taskType,
            String keyword,
            Boolean success,
            LocalDateTime startTime,
            LocalDateTime endTime,
            int page,
            int size
    ) {
        int safePage = Math.max(page, 0);
        int safeSize = Math.min(Math.max(size, 1), 100);
        Pageable pageable = PageRequest.of(safePage, safeSize, Sort.by(Sort.Direction.DESC, "createdAt"));

        return recordRepository.search(
                blankToNull(taskType),
                userId,
                isAdmin(role),
                blankToNull(keyword),
                startTime,
                endTime,
                success,
                pageable
        ).map(this::toResponse);
    }

    public RecognitionRecordResponse getRecordDetail(Long userId, String role, Long id) {
        return recordRepository.findAccessibleById(id, userId, isAdmin(role))
                .map(this::toResponse)
                .orElseThrow(() -> new RuntimeException("记录不存在: " + id));
    }

    private RecognitionRecordResponse toResponse(InferenceRecord record) {
        JsonNode summary = parseSummary(record.getResultJson());
        Double confidence = summary != null && summary.path("confidence").isNumber()
                ? summary.path("confidence").doubleValue()
                : null;
        String target = summary == null ? "" : summary.path("target").asText("");
        if (target.isBlank()) {
            if (!Boolean.TRUE.equals(record.getSuccess())) {
                target = record.getErrorMessage() == null || record.getErrorMessage().isBlank()
                        ? "识别失败"
                        : record.getErrorMessage();
            } else if (record.getDetectionCount() != null && record.getDetectionCount() > 0) {
                target = "检测到 " + record.getDetectionCount() + " 个目标";
            } else {
                target = "未检测到目标";
            }
        }

        String status;
        if (!Boolean.TRUE.equals(record.getSuccess())) {
            status = "failed";
        } else if (confidence != null && confidence < 0.5) {
            status = "warning";
        } else {
            status = "completed";
        }

        return RecognitionRecordResponse.builder()
                .id(record.getId())
                .createdAt(record.getCreatedAt())
                .taskType(record.getTaskType())
                .target(target)
                .confidence(confidence)
                .durationMs(record.getLatencyMs())
                .detectionCount(record.getDetectionCount())
                .success(record.getSuccess())
                .status(status)
                .errorMessage(record.getErrorMessage())
                .build();
    }

    private JsonNode parseSummary(String json) {
        if (json == null || json.isBlank()) return null;
        try {
            return objectMapper.readTree(json);
        } catch (Exception error) {
            log.warn("历史记录摘要解析失败: {}", error.getMessage());
            return null;
        }
    }

    private String blankToNull(String value) {
        if (value == null || value.isBlank()) return null;
        return value.trim();
    }

    private boolean isAdmin(String role) {
        return "ADMIN".equalsIgnoreCase(role);
    }
}
