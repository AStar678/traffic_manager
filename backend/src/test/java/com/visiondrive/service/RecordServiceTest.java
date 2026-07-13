package com.visiondrive.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.dto.RecognitionRecordResponse;
import com.visiondrive.model.entity.InferenceRecord;
import com.visiondrive.repository.InferenceRecordRepository;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;

import java.lang.reflect.Proxy;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

class RecordServiceTest {

    @Test
    void queriesOnlyCurrentUserAndMapsSafeResponse() {
        InferenceRecord record = record(41L, 7L, true, "{\"target\":\"浙C79D21\",\"confidence\":0.88}");
        AtomicReference<Object[]> searchArguments = new AtomicReference<>();
        InferenceRecordRepository recordRepository = repository((method, args) -> {
            if (!"search".equals(method)) return null;
            searchArguments.set(args);
            return new PageImpl<>(List.of(record));
        });
        RecordService service = new RecordService(recordRepository, new ObjectMapper());

        Page<RecognitionRecordResponse> result = service.queryRecords(
                7L, "USER", "license_plate", " 浙C ", true, null, null, 0, 20
        );

        assertThat(result.getTotalElements()).isEqualTo(1);
        RecognitionRecordResponse response = result.getContent().get(0);
        assertThat(response.getTarget()).isEqualTo("浙C79D21");
        assertThat(response.getConfidence()).isEqualTo(0.88);
        assertThat(response.getStatus()).isEqualTo("completed");
        assertThat(searchArguments.get()[0]).isEqualTo("license_plate");
        assertThat(searchArguments.get()[1]).isEqualTo(7L);
        assertThat(searchArguments.get()[2]).isEqualTo(false);
        assertThat(searchArguments.get()[3]).isEqualTo("浙C");
        assertThat(searchArguments.get()[6]).isEqualTo(true);
    }

    @Test
    void recordDetailRequiresMatchingUserId() {
        InferenceRecord record = record(52L, 11L, false, "{}");
        record.setErrorMessage("算法超时");
        AtomicReference<Object[]> detailArguments = new AtomicReference<>();
        InferenceRecordRepository recordRepository = repository((method, args) -> {
            if (!"findAccessibleById".equals(method)) return null;
            detailArguments.set(args);
            return Optional.of(record);
        });
        RecordService service = new RecordService(recordRepository, new ObjectMapper());

        RecognitionRecordResponse response = service.getRecordDetail(11L, "USER", 52L);

        assertThat(response.getTarget()).isEqualTo("算法超时");
        assertThat(response.getStatus()).isEqualTo("failed");
        assertThat(detailArguments.get()).containsExactly(52L, 11L, false);
    }

    @Test
    void adminCanReadUnassignedLegacyRecords() {
        InferenceRecord record = record(63L, null, true, "{\"target\":\"历史记录\"}");
        AtomicReference<Object[]> searchArguments = new AtomicReference<>();
        InferenceRecordRepository recordRepository = repository((method, args) -> {
            if (!"search".equals(method)) return null;
            searchArguments.set(args);
            return new PageImpl<>(List.of(record));
        });
        RecordService service = new RecordService(recordRepository, new ObjectMapper());

        Page<RecognitionRecordResponse> result = service.queryRecords(
                5L, "ADMIN", null, null, null, null, null, 0, 20
        );

        assertThat(result.getContent().get(0).getTarget()).isEqualTo("历史记录");
        assertThat(searchArguments.get()[2]).isEqualTo(true);
    }

    private InferenceRecord record(Long id, Long userId, boolean success, String resultJson) {
        InferenceRecord record = new InferenceRecord();
        record.setId(id);
        record.setUserId(userId);
        record.setTaskType("license_plate");
        record.setSuccess(success);
        record.setResultJson(resultJson);
        record.setDetectionCount(success ? 1 : 0);
        record.setLatencyMs(320L);
        record.setCreatedAt(LocalDateTime.of(2026, 7, 13, 16, 1));
        return record;
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
