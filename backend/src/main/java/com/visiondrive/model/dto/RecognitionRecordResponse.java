package com.visiondrive.model.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class RecognitionRecordResponse {
    private Long id;
    private LocalDateTime createdAt;
    private String taskType;
    private String target;
    private Double confidence;
    private Long durationMs;
    private Integer detectionCount;
    private Boolean success;
    private String status;
    private String errorMessage;
}
