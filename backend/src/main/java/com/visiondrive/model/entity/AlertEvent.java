package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "alert_event")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AlertEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String alertId;

    @Column(nullable = false)
    private String severity;  // info / warning / critical

    private String title;

    @Column(columnDefinition = "TEXT")
    private String summary;

    private String anomalyType;

    private String affectedModule;

    @Column(columnDefinition = "TEXT")
    private String metrics;

    @Column(columnDefinition = "TEXT")
    private String suggestedActions;

    private Boolean resolved = false;

    private LocalDateTime resolvedAt;

    @CreationTimestamp
    private LocalDateTime createdAt;
}