package com.visiondrive.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.InferenceRequest;
import com.visiondrive.model.dto.InferenceResponse;
import com.visiondrive.model.entity.InferenceRecord;
import com.visiondrive.repository.InferenceRecordRepository;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Proxy;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

class RecognitionHistoryServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void storesAuthenticatedUserAndSafeInferenceSummary() throws Exception {
        AtomicReference<InferenceRecord> captured = new AtomicReference<>();
        InferenceRecordRepository recordRepository = repository((method, args) -> {
            if (!"save".equals(method)) return null;
            InferenceRecord record = (InferenceRecord) args[0];
            record.setId(88L);
            captured.set(record);
            return record;
        });
        RecognitionHistoryService service = new RecognitionHistoryService(recordRepository, objectMapper);

        InferenceRequest request = new InferenceRequest();
        request.setTaskType("license_plate");
        request.setImageUrl("/srv/private/camera-1.jpg");
        InferenceResponse.Detection detection = new InferenceResponse.Detection();
        detection.setPlateNumber("京A12345");
        detection.setConfidence(0.96);
        InferenceResponse.InferenceData data = new InferenceResponse.InferenceData();
        data.setDetections(List.of(detection));
        data.setDetectionCount(1);
        InferenceResponse response = new InferenceResponse();
        response.setData(data);

        service.saveInference(7L, request, response, "trace-1", 312, true, null);

        InferenceRecord saved = captured.get();
        assertThat(saved).isNotNull();
        assertThat(saved.getUserId()).isEqualTo(7L);
        assertThat(saved.getTaskType()).isEqualTo("license_plate");
        assertThat(saved.getDetectionCount()).isEqualTo(1);
        JsonNode summary = objectMapper.readTree(saved.getResultJson());
        assertThat(summary.path("target").asText()).isEqualTo("京A12345");
        assertThat(summary.path("confidence").asDouble()).isEqualTo(0.96);
        assertThat(saved.getResultJson()).doesNotContain("/srv/private");
    }

    @Test
    void storesOwnerGestureInUnifiedHistory() throws Exception {
        AtomicReference<InferenceRecord> captured = new AtomicReference<>();
        InferenceRecordRepository recordRepository = repository((method, args) -> {
            if (!"save".equals(method)) return null;
            captured.set((InferenceRecord) args[0]);
            return args[0];
        });
        RecognitionHistoryService service = new RecognitionHistoryService(recordRepository, objectMapper);

        service.saveOwnerGesture(
                9L,
                Map.of("gestureName", "调节音量", "confidence", 0.91, "matched", true),
                "trace-owner",
                145,
                true,
                null
        );

        InferenceRecord saved = captured.get();
        assertThat(saved).isNotNull();
        assertThat(saved.getUserId()).isEqualTo(9L);
        assertThat(saved.getTaskType()).isEqualTo("owner_gesture");
        assertThat(saved.getDetectionCount()).isEqualTo(1);
        assertThat(objectMapper.readTree(saved.getResultJson()).path("target").asText()).isEqualTo("调节音量");
    }

    @Test
    void refusesToCreateUnownedHistory() {
        AtomicReference<InferenceRecord> captured = new AtomicReference<>();
        InferenceRecordRepository recordRepository = repository((method, args) -> {
            if ("save".equals(method)) captured.set((InferenceRecord) args[0]);
            return null;
        });
        RecognitionHistoryService service = new RecognitionHistoryService(recordRepository, objectMapper);
        InferenceRequest request = new InferenceRequest();
        request.setTaskType("police_gesture");

        service.saveInference(null, request, null, "trace-missing-user", 10, false, "failed");

        assertThat(captured.get()).isNull();
    }

    @SuppressWarnings("unchecked")
    private InferenceRecordRepository repository(RepositoryCall call) {
        return (InferenceRecordRepository) Proxy.newProxyInstance(
                InferenceRecordRepository.class.getClassLoader(),
                new Class<?>[]{InferenceRecordRepository.class},
                (proxy, method, args) -> call.invoke(method.getName(), args)
        );
    }

    @FunctionalInterface
    private interface RepositoryCall {
        Object invoke(String method, Object[] args);
    }
}
