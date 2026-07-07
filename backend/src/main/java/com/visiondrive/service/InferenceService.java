package com.visiondrive.service;

import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.model.dto.InferenceRequest;
import com.visiondrive.model.dto.InferenceResponse;
import com.visiondrive.model.entity.InferenceRecord;
import com.visiondrive.model.entity.DetectionResult;
import com.visiondrive.repository.InferenceRecordRepository;
import com.visiondrive.repository.DetectionResultRepository;
import com.visiondrive.common.utils.JsonLogBuilder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class InferenceService {

    private final AlgorithmClient algorithmClient;
    private final InferenceRecordRepository recordRepository;
    private final DetectionResultRepository detectionResultRepository;

    /**
     * 处理图片推理
     */
    @Transactional
    public InferenceResponse processImageInference(InferenceRequest request) {
        long startTime = System.currentTimeMillis();
        String traceId = JsonLogBuilder.generateTraceId();

        log.info("开始推理: traceId={}, taskType={}, imageUrl={}",
                traceId, request.getTaskType(), request.getImageUrl());

        try {
        // 调用算法客户端
        InferenceResponse response = algorithmClient.callImageInference(
                request.getTaskType(),
                request.getImageUrl()
        );

            // 2. 保存识别记录到数据库
            saveInferenceRecord(request, response, traceId,
                    System.currentTimeMillis() - startTime, true, null);

            log.info("推理完成: traceId={}, detectionCount={}, latency={}ms",
                    traceId, response.getData() != null ? response.getData().getDetectionCount() : 0);

            return response;

        } catch (Exception e) {
            log.error("推理失败: traceId={}, error={}", traceId, e.getMessage());
            // 保存失败记录
            saveInferenceRecord(request, null, traceId,
                    System.currentTimeMillis() - startTime, false, e.getMessage());
            throw new RuntimeException("推理失败: " + e.getMessage());
        }
    }

    /**
     * 保存推理记录到数据库
     */
    private void saveInferenceRecord(
            InferenceRequest request,
            InferenceResponse response,
            String traceId,
            long latencyMs,
            boolean success,
            String errorMessage
    ) {
        try {
            // 1. 保存主记录
            InferenceRecord record = new InferenceRecord();
            record.setTraceId(traceId);
            record.setTaskType(request.getTaskType());
            record.setInputType("image");
            record.setInputUrl(request.getImageUrl());
            record.setLatencyMs(latencyMs);
            record.setSuccess(success);
            record.setErrorMessage(errorMessage);
            record.setCreatedAt(LocalDateTime.now());
            // record.setUserId(1L);  // 等认证完成后从SecurityContext获取

            if (success && response != null && response.getData() != null) {
                record.setResultUrl(response.getData().getAnnotatedImageUrl());
                record.setDetectionCount(response.getData().getDetectionCount());
                record.setResultJson(JsonLogBuilder.toJson(response));
            }

            InferenceRecord saved = recordRepository.save(record);

            // 2. 保存检测结果详情（如果是车牌识别）
            if (success && response != null && response.getData() != null) {
                List<DetectionResult> results = new ArrayList<>();
                // 根据不同任务类型解析detections
                // ... 具体解析逻辑
                detectionResultRepository.saveAll(results);
            }

            log.info("记录保存成功: recordId={}", saved.getId());

        } catch (Exception e) {
            log.error("保存记录失败: {}", e.getMessage());
        }
    }
}