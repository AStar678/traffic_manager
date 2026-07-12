package com.visiondrive.model.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "user_gesture_recognition_result")
@NoArgsConstructor
public class UserGestureRecognitionResult extends RecognitionResultRecord {
}
