package com.visiondrive.service;

import com.visiondrive.common.utils.JsonLogBuilder;
import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.repository.SystemLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class SystemLogService {

    private final SystemLogRepository systemLogRepository;

    public void info(String module, String event, Map<String, Object> detail) {
        record("INFO", module, event, JsonLogBuilder.toJson(detail), null, null);
    }

    public void warn(String module, String event, Map<String, Object> detail) {
        record("WARN", module, event, JsonLogBuilder.toJson(detail), null, null);
    }

    public void error(String module, String event, Map<String, Object> detail) {
        record("ERROR", module, event, JsonLogBuilder.toJson(detail), null, null);
    }

    public void record(String level, String module, String event, String detail) {
        record(level, module, event, detail, null, null);
    }

    public void record(String level, String module, String event, String detail, Long userId, String traceId) {
        try {
            SystemLog systemLog = new SystemLog();
            systemLog.setTraceId(traceId == null || traceId.isBlank() ? JsonLogBuilder.generateTraceId() : traceId);
            systemLog.setLevel(level);
            systemLog.setModule(module);
            systemLog.setEvent(event);
            systemLog.setDetail(detail);
            systemLog.setUserId(userId);
            systemLogRepository.save(systemLog);
        } catch (Exception e) {
            log.warn("系统日志写入失败: module={}, event={}, error={}", module, event, e.getMessage());
        }
    }
}
