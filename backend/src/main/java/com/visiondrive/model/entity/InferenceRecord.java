package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "inference_record")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class InferenceRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String traceId;
    private String taskType;
    private String inputType;
    private String inputUrl;
    private String resultUrl;
    private String resultJson;
    private Integer detectionCount;
    private Long latencyMs;
    private Boolean success;
    private String errorMessage;
    private Long userId;

    @CreationTimestamp
    private LocalDateTime createdAt;
}