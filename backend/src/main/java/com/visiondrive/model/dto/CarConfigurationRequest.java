package com.visiondrive.model.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CarConfigurationRequest {
    @NotNull @DecimalMin("16.0") @DecimalMax("30.0")
    private Double climateTemperature;
    @NotBlank
    private String climateMode;
    @NotNull @Min(0) @Max(100)
    private Integer audioVolume;
    @NotBlank
    private String audioTrack;
    @NotNull
    private Boolean systemAwake;
    @NotBlank
    private String activeModule;
    @NotBlank
    private String phoneStatus;
    @NotBlank
    private String phoneCaller;
    @NotNull @Min(0) @Max(300)
    private Integer speed;
    @NotBlank
    private String gear;
    @NotNull @DecimalMin("0.0") @DecimalMax("5.0")
    private Double tireFrontLeft;
    @NotNull @DecimalMin("0.0") @DecimalMax("5.0")
    private Double tireFrontRight;
    @NotNull @DecimalMin("0.0") @DecimalMax("5.0")
    private Double tireRearLeft;
    @NotNull @DecimalMin("0.0") @DecimalMax("5.0")
    private Double tireRearRight;
}
