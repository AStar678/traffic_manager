package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import java.util.List;

@Data  //
@Schema(description = "图片推理请求")
public class InferenceRequest {

    @Schema(description = "任务类型: license_plate；手势识别请使用 /api/v1/owner-gestures",
            example = "license_plate")
    @NotBlank(message = "任务类型不能为空")
    private String taskType;

    @Schema(description = "图片URL",
            example = "http://localhost:8080/api/files/images/2026-07-07/abc.jpg")
    @NotBlank(message = "图片URL不能为空")
    private String imageUrl;
}
