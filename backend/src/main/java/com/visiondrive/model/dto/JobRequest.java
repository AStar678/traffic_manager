package com.visiondrive.model.dto;

import lombok.Data;

@Data
public class JobRequest {
    private String taskType;
    private JobInput input;
    private String callbackUrl;
    private JobOptions options;

    @Data
    public static class JobInput {
        private String type;  // video_file
        private String url;
    }

    @Data
    public static class JobOptions {
        private Integer sampleFps;
        private Double confidenceThreshold;
        private Boolean generateAnnotatedVideo;
    }
}