package com.visiondrive.model.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class MultiCameraInferenceResponse {
    private String taskType;
    private Long latencyMs;
    private Long serverTimeMs;
    private Integer detectionCount;
    private List<InferenceResponse.Detection> detections = new ArrayList<>();
    private List<CameraInferenceResult> cameras = new ArrayList<>();

    @Data
    public static class CameraInferenceResult {
        private Integer slotId;
        private String cameraName;
        private String sourceType;
        private String status;
        private String error;
        private String frameUrl;
        private String frameId;
        private Long framePts;
        private String frameTimeBase;
        private Long frameCapturedAtMs;
        private InferenceResponse.InferenceData result;
    }
}
