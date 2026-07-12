package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "car", uniqueConstraints = @UniqueConstraint(name = "uk_car_user", columnNames = "user_id"))
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Car {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false, updatable = false)
    private User user;

    @Column(nullable = false)
    private Double climateTemperature = 24.0;

    @Column(nullable = false, length = 32)
    private String climateMode = "Auto";

    @Column(nullable = false)
    private Integer audioVolume = 42;

    @Column(nullable = false, length = 128)
    private String audioTrack = "City Drive";

    @Column(nullable = false)
    private Boolean systemAwake = true;

    @Column(nullable = false, length = 32)
    private String activeModule = "驾驶";

    @Column(nullable = false, length = 32)
    private String phoneStatus = "待机";

    @Column(nullable = false, length = 64)
    private String phoneCaller = "无来电";

    @Column(nullable = false)
    private Integer speed = 42;

    @Column(nullable = false, length = 8)
    private String gear = "D";

    @Column(nullable = false)
    private Double tireFrontLeft = 2.4;

    @Column(nullable = false)
    private Double tireFrontRight = 2.4;

    @Column(nullable = false)
    private Double tireRearLeft = 2.3;

    @Column(nullable = false)
    private Double tireRearRight = 2.1;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
