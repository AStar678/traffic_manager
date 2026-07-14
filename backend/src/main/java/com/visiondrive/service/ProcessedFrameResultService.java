package com.visiondrive.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.InferenceResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Publishes compact, frame-addressed inference manifests for server-side renderers.
 *
 * <p>The algorithm result is written next to the shared camera frames instead of
 * being sent back from the browser for drawing.  A temporary file + atomic rename
 * prevents the WebRTC process from observing a partially-written JSON document.</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ProcessedFrameResultService {

    private final ObjectMapper objectMapper;

    @Value("${camera.frame-dir:./uploads/camera-frames}")
    private String frameDir;

    public void publish(
            String taskType,
            CameraManagerService.CameraFrame frame,
            InferenceResponse.InferenceData data
    ) {
        if (data == null || !isSupportedTask(taskType)) return;

        Path directory = Path.of(frameDir).toAbsolutePath().normalize().resolve("processed-results");
        Path output = directory.resolve(taskType + "-camera-" + frame.slotId() + ".json");
        Path temporary = directory.resolve("." + output.getFileName() + "." + UUID.randomUUID() + ".tmp");

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("taskType", taskType);
        payload.put("slotId", frame.slotId());
        payload.put("cameraName", frame.cameraName());
        payload.put("sourceType", frame.sourceType());
        payload.put("frameId", frame.frameId());
        payload.put("framePts", frame.framePts());
        payload.put("frameTimeBase", frame.frameTimeBase());
        payload.put("frameCapturedAtMs", frame.frameCapturedAtMs());
        payload.put("framePath", frame.path().toAbsolutePath().normalize().toString());
        payload.put("publishedAtMs", System.currentTimeMillis());
        payload.put("image", data.getImage());
        payload.put("detections", data.getDetections());
        payload.put("detectionCount", data.getDetectionCount());
        payload.put("latencyMs", data.getLatencyMs());

        try {
            Files.createDirectories(directory);
            objectMapper.writeValue(temporary.toFile(), payload);
            moveAtomically(temporary, output);
        } catch (Exception error) {
            try {
                Files.deleteIfExists(temporary);
            } catch (IOException ignored) {
                // Best-effort cleanup; publishing must never fail the inference response.
            }
            log.warn("发布后端叠框结果失败: taskType={}, slotId={}, error={}",
                    taskType, frame.slotId(), error.getMessage());
        }
    }

    private void moveAtomically(Path source, Path target) throws IOException {
        try {
            Files.move(source, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException ignored) {
            Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private boolean isSupportedTask(String taskType) {
        return "license_plate".equals(taskType)
                || "vehicle_type".equals(taskType)
                || "police_gesture".equals(taskType);
    }
}
