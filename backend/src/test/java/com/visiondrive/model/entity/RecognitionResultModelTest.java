package com.visiondrive.model.entity;

import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Table;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;

class RecognitionResultModelTest {

    @Test
    void mapsThreeTablesAndCompositePrimaryKey() throws NoSuchFieldException {
        assertThat(LicensePlateRecognitionResult.class.getAnnotation(Table.class).name())
                .isEqualTo("license_plate_recognition_result");
        assertThat(PoliceGestureRecognitionResult.class.getAnnotation(Table.class).name())
                .isEqualTo("police_gesture_recognition_result");
        assertThat(UserGestureRecognitionResult.class.getAnnotation(Table.class).name())
                .isEqualTo("user_gesture_recognition_result");

        assertThat(RecognitionResultRecord.class.getDeclaredField("id").getAnnotation(EmbeddedId.class))
                .isNotNull();

        LocalDateTime createdAt = LocalDateTime.of(2026, 7, 12, 9, 30, 0, 123_456_000);
        RecognitionResultId id = new RecognitionResultId(7L, createdAt);
        assertThat(id.getUserId()).isEqualTo(7L);
        assertThat(id.getCreatedAt()).isEqualTo(createdAt);
    }

    @Test
    void storesRecognitionResultAndImageSource() {
        LicensePlateRecognitionResult result = new LicensePlateRecognitionResult();
        result.setRecognitionResult("{\"plateNumber\":\"京A12345\",\"confidence\":0.98}");
        result.setImageSource("camera://sandtable/live5");

        assertThat(result.getRecognitionResult()).contains("京A12345");
        assertThat(result.getImageSource()).isEqualTo("camera://sandtable/live5");
    }
}
