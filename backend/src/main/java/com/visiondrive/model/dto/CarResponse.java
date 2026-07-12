package com.visiondrive.model.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CarResponse {
    private Long id;
    private Double climateTemperature;
    private String climateMode;
    private Integer audioVolume;
    private String audioTrack;
    private Boolean systemAwake;
    private String activeModule;
    private String phoneStatus;
    private String phoneCaller;
    private Integer speed;
    private String gear;
    private Double tireFrontLeft;
    private Double tireFrontRight;
    private Double tireRearLeft;
    private Double tireRearRight;
    private LocalDateTime updatedAt;
}
