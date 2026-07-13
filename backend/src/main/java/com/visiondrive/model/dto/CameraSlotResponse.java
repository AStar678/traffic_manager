package com.visiondrive.model.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CameraSlotResponse {
    private Integer slotId;
    private String name;
    private String sourceType;
    private String path;
    private Integer deviceIndex;
    private Boolean weatherSimulationEnabled;
    private String status;
    private String error;
    private String frameUrl;
}
