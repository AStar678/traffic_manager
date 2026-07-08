package com.visiondrive.service;

import com.visiondrive.model.entity.InferenceRecord;
import com.visiondrive.repository.InferenceRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class RecordService {

    private final InferenceRecordRepository recordRepository;

    public Page<InferenceRecord> queryRecords(
            String taskType,
            Boolean success,
            LocalDateTime startTime,
            LocalDateTime endTime,
            int page,
            int size
    ) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));

        // 使用 Repository 中的搜索方法
        return recordRepository.search(taskType, null, startTime, endTime, success, pageable);
    }

    public InferenceRecord getRecordDetail(Long id) {
        return recordRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("记录不存在: " + id));
    }
}