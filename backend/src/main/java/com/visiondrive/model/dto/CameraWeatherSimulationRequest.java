package com.visiondrive.model.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CameraWeatherSimulationRequest {
    @NotNull(message = "请指定是否开启模拟雨雪")
    private Boolean enabled;
}
