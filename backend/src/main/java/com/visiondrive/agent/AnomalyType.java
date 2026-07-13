package com.visiondrive.agent;

/**
 * 异常类型枚举。
 */
public enum AnomalyType {

    // 1. 车牌识别连续失败（1分钟失败率 > 30%）
    LICENSE_PLATE_FAILURE_RATE("车牌识别失败率过高", "license_plate"),

    // 2. 车牌识别全面故障（3分钟成功率 < 10%）
    LICENSE_PLATE_CRITICAL_FAILURE("车牌识别全面故障", "license_plate"),

    // 3. 手势识别置信度持续偏低（5分钟均值 < 0.5）
    GESTURE_CONFIDENCE_LOW("手势识别置信度持续偏低", "gesture"),

    // 4. LLM API 超时（>30秒 或 1分钟 ≥3次）
    LLM_TIMEOUT("LLM API 超时", "llm"),

    // 5. LLM Token 超额（80%/100% 阈值）
    LLM_TOKEN_EXCEEDED("LLM Token 超额", "llm"),

    // 6. 未授权访问
    UNAUTHORIZED_ACCESS("未授权访问", "auth"),

    // 7. 数据库连接失败
    DATABASE_CONNECTION_FAILURE("数据库连接失败", "database"),

    // 8. CPU/内存过高
    SYSTEM_RESOURCE_HIGH("系统资源占用过高", "system"),

    // 9. 低置信度或失败识别由千问视觉模型完成二次复核
    RECOGNITION_FAILURE_REVIEW("识别失败 Agent 复核", "inference");

    private final String description;
    private final String module;

    AnomalyType(String description, String module) {
        this.description = description;
        this.module = module;
    }

    public String getDescription() {
        return description;
    }

    public String getModule() {
        return module;
    }
}
