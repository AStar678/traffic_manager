package com.visiondrive.model.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import lombok.Data;

@Data
public class JobRequest {
    @JsonAlias("task_type")
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
