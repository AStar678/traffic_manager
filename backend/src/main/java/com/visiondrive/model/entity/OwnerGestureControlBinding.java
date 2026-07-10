package com.visiondrive.model.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "owner_gesture_control_binding")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OwnerGestureControlBinding {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 96)
    private String gestureCode;

    @Column(nullable = false, length = 128)
    private String gestureName;

    @Column(length = 32)
    private String gestureKind;

    @Column(length = 32)
    private String gestureSource;

    @Column(nullable = false, length = 48)
    private String actionType = "NONE";

    @Column(nullable = false)
    private Boolean enabled = false;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
