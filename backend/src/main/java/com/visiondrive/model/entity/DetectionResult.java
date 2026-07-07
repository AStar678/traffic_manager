package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Entity
@Table(name = "detection_result")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DetectionResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long recordId;  // 关联 inference_record 表

    private String objectId;

    private String objectType;

    private Integer x1;
    private Integer y1;
    private Integer x2;
    private Integer y2;

    @Column(columnDefinition = "TEXT")
    private String attributes;  // 存储JSON

    private Double confidence;
}