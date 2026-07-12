package com.visiondrive.model.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "police_gesture_recognition_result")
@NoArgsConstructor
public class PoliceGestureRecognitionResult extends RecognitionResultRecord {
}
