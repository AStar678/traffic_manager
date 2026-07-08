package com.visiondrive.agent;

import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
public class AlertClassifier {

    /**
     * 根据异常类型决定告警级别
     */
    public AlertSeverity classify(AnomalyType type, Map<String, Object> context) {
        switch (type) {
            case LICENSE_PLATE_CRITICAL_FAILURE:
            case UNAUTHORIZED_ACCESS:
            case DATABASE_CONNECTION_FAILURE:
                return AlertSeverity.CRITICAL;

            case LICENSE_PLATE_FAILURE_RATE:
            case GESTURE_CONFIDENCE_LOW:
            case LLM_TIMEOUT:
            case LLM_TOKEN_EXCEEDED:
            case SYSTEM_RESOURCE_HIGH:
                // 根据上下文判断
                if (context.containsKey("severity") && "critical".equals(context.get("severity"))) {
                    return AlertSeverity.CRITICAL;
                }
                return AlertSeverity.WARNING;

            default:
                return AlertSeverity.INFO;
        }
    }
}