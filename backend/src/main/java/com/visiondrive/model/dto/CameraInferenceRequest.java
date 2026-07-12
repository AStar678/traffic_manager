package com.visiondrive.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CameraInferenceRequest {
    @NotBlank(message = "任务类型不能为空")
    private String taskType;
}
