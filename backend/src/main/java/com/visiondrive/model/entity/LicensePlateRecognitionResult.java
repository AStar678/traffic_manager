package com.visiondrive.model.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "license_plate_recognition_result")
@NoArgsConstructor
public class LicensePlateRecognitionResult extends RecognitionResultRecord {
}
