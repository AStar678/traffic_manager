package com.visiondrive.common.utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;

/**
 * // JSON格式日志构建工具
 */
@Slf4j
public class JsonLogBuilder {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 生成追踪ID
     */
    public static String generateTraceId() {
        return "trace_" + System.currentTimeMillis() + "_" + System.nanoTime() % 10000;
    }

    /**
     * 对象转JSON字符串
     */
    public static String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            log.error("JSON序列化失败: {}", e.getMessage());
            return "{}";
        }
    }
}