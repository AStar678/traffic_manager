package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "system_log")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SystemLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String traceId;

    @Column(nullable = false)
    private String level;  // INFO / WARN / ERROR

    private String module;  // license_plate / gesture / llm / auth / database / system

    private String event;   // timeout / unauthorized / connection_error / failure / success

    @Column(columnDefinition = "TEXT")
    private String detail;

    private Long userId;

    @CreationTimestamp
    private LocalDateTime createdAt;
}