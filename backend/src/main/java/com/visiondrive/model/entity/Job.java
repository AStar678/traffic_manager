package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "job")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Job {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String jobId;

    @Column(nullable = false)
    private String taskType;  // license_plate / owner_gesture

    @Column(columnDefinition = "TEXT")
    private String inputUrl;

    @Column(nullable = false)
    private String status;  // queued / processing / completed / failed / cancelled

    private Integer progress = 0;

    private Integer processedFrames = 0;

    private Integer totalFrames = 0;

    @Column(columnDefinition = "TEXT")
    private String resultUrl;

    @Column(columnDefinition = "TEXT")
    private String errorMessage;

    private Long userId;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
