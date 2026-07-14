package com.visiondrive.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.InferenceResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ProcessedFrameResultServiceTest {

    @TempDir
    Path tempDir;

    @Test
    void publishesCompactFrameAddressedManifest() throws Exception {
        ObjectMapper objectMapper = new ObjectMapper();
        ProcessedFrameResultService service = new ProcessedFrameResultService(objectMapper);
        ReflectionTestUtils.setField(service, "frameDir", tempDir.toString());

        InferenceResponse.Bbox bbox = new InferenceResponse.Bbox();
        bbox.setX1(10);
        bbox.setY1(20);
        bbox.setX2(110);
        bbox.setY2(70);
        InferenceResponse.Detection detection = new InferenceResponse.Detection();
        detection.setObjectId("plate_001");
        detection.setPlateNumber("TEST123");
        detection.setBbox(bbox);

        InferenceResponse.ImageInfo image = new InferenceResponse.ImageInfo();
        image.setWidth(1280);
        image.setHeight(720);
        InferenceResponse.InferenceData data = new InferenceResponse.InferenceData();
        data.setImage(image);
        data.setDetections(List.of(detection));
        data.setDetectionCount(1);
        data.setAnnotatedImageUrl("data:image/jpeg;base64,should-not-be-published");

        CameraManagerService.CameraFrame frame = new CameraManagerService.CameraFrame(
                1, "camera", "VIDEO", tempDir.resolve("frame.jpg"), "/frame.jpg",
                "1-90000-1", 90000L, "1/90000", 1_700_000_000_000L
        );
        service.publish("license_plate", frame, data);

        Path manifest = tempDir.resolve("processed-results/license_plate-camera-1.json");
        assertTrue(Files.isRegularFile(manifest));
        JsonNode json = objectMapper.readTree(manifest.toFile());
        assertEquals(90000L, json.path("framePts").asLong());
        assertEquals("VIDEO", json.path("sourceType").asText());
        assertEquals(tempDir.resolve("frame.jpg").toAbsolutePath().normalize().toString(), json.path("framePath").asText());
        assertEquals("TEST123", json.path("detections").get(0).path("plateNumber").asText());
        assertFalse(json.has("annotatedImageUrl"));
    }
}
