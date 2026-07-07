package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

@Data
@Schema(description = "图片推理响应")
public class InferenceResponse {

    @Schema(description = "状态码")
    private Integer code;

    @Schema(description = "消息")
    private String message;

    @Schema(description = "请求ID")
    private String requestId;

    @Schema(description = "时间戳")
    private String timestamp;

    @Schema(description = "业务数据")
    private InferenceData data;

    @Data
    public static class InferenceData {
        private String taskType;
        private Long latencyMs;
        private ImageInfo image;
        private List<Detection> detections;
        private Integer detectionCount;
        private String annotatedImageUrl;
    }

    @Data
    public static class ImageInfo {
        private Integer width;
        private Integer height;
    }

    @Data
    public static class Detection {
        private String objectId;
        private String objectType;
        private Bbox bbox;
        private String plateNumber;
        private String plateColor;
        private Double confidence;
        private String gestureCode;
        private String gestureName;
        private List<Keypoint> keypoints;
    }

    @Data
    public static class Bbox {
        private Integer x1;
        private Integer y1;
        private Integer x2;
        private Integer y2;
    }

    @Data
    public static class Keypoint {
        private String name;
        private Integer x;
        private Integer y;
        private Double score;
    }
}