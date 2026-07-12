package com.visiondrive.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CameraSlotRequest {
    @NotBlank(message = "摄像头输入类型不能为空")
    private String sourceType;
    private String name;
    private String path;
    private Integer deviceIndex;
}
