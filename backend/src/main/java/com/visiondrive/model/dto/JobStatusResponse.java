package com.visiondrive.model.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
public class JobStatusResponse {
    private String jobId;
    private String taskType;
    private String status;  // queued / processing / completed / failed / cancelled
    private Integer progress;
    private Integer processedFrames;
    private Integer totalFrames;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 简化构造（创建时使用）
    public JobStatusResponse(String jobId, String status) {
        this.jobId = jobId;
        this.status = status;
    }
}