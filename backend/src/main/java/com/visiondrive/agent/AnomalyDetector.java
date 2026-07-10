package com.visiondrive.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.repository.SystemLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.lang.management.ManagementFactory;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Objects;

@Slf4j
@Component
@RequiredArgsConstructor
public class AnomalyDetector {

    private final SystemLogRepository systemLogRepository;
    private final ObjectMapper objectMapper;

    @Value("${alert.agent.failure-rate-threshold:0.3}")
    private double failureRateThreshold;

    @Value("${alert.agent.low-confidence-threshold:0.5}")
    private double lowConfidenceThreshold;

    @Value("${alert.agent.token-limit:1000000}")
    private long tokenLimit;

    /**
     * 检测所有类型的异常
     */
    public List<AnomalyEvent> detectAll() {
        List<AnomalyEvent> events = new ArrayList<>();

        // 1. 检测车牌识别失败率
        detectLicensePlateFailureRate(events);

        // 2. 检测车牌识别全面故障
        detectLicensePlateCriticalFailure(events);

        // 3. 检测手势识别置信度持续偏低
        detectGestureConfidenceLow(events);

        // 4. 检测 LLM API 超时
        detectLlmTimeout(events);

        // 5. 检测 LLM Token 超额
        detectLlmTokenExceeded(events);

        // 6. 检测未授权访问
        detectUnauthorizedAccess(events);

        // 7. 检测数据库连接失败
        detectDatabaseConnectionFailure(events);

        // 8. 检测系统资源过高
        detectSystemResourceHigh(events);

        return events;
    }

    // ============================================================
    // 1. 车牌识别连续失败（1分钟失败率 > 30%）
    // ============================================================
    private void detectLicensePlateFailureRate(List<AnomalyEvent> events) {
        LocalDateTime oneMinuteAgo = LocalDateTime.now().minusMinutes(1);
        List<SystemLog> logs = systemLogRepository.findByModuleAndCreatedAtAfter("license_plate", oneMinuteAgo);

        long total = logs.size();
        if (total == 0) return;

        long failures = logs.stream()
                .filter(log -> log.getEvent() != null && log.getEvent().contains("failure"))
                .count();

        double failureRate = (double) failures / total;
        if (failureRate > failureRateThreshold) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.LICENSE_PLATE_FAILURE_RATE);
            event.setSeverity(AlertSeverity.WARNING);
            event.setTitle("车牌识别失败率过高");
            event.setSummary(String.format("过去1分钟内车牌识别失败率 %.1f%%，超过 %.0f%% 阈值",
                    failureRate * 100, failureRateThreshold * 100));
            event.setMetrics(String.format("{\"total\":%d,\"failures\":%d,\"rate\":%.2f}", total, failures, failureRate));
            event.setSuggestedActions("1. 检查输入图片质量\n2. 确认算法服务是否正常运行\n3. 检查模型是否加载成功");
            events.add(event);
        }
    }

    // ============================================================
    // 2. 车牌识别全面故障（3分钟成功率 < 10%）
    // ============================================================
    private void detectLicensePlateCriticalFailure(List<AnomalyEvent> events) {
        LocalDateTime threeMinutesAgo = LocalDateTime.now().minusMinutes(3);
        List<SystemLog> logs = systemLogRepository.findByModuleAndCreatedAtAfter("license_plate", threeMinutesAgo);

        long total = logs.size();
        if (total < 10) return;  // 样本太少不检测

        long successes = logs.stream()
                .filter(log -> log.getEvent() != null && log.getEvent().contains("success"))
                .count();

        double successRate = (double) successes / total;
        if (successRate < 0.1) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.LICENSE_PLATE_CRITICAL_FAILURE);
            event.setSeverity(AlertSeverity.CRITICAL);
            event.setTitle("车牌识别全面故障");
            event.setSummary(String.format("过去3分钟内车牌识别成功率仅 %.1f%%，低于10%%阈值", successRate * 100));
            event.setMetrics(String.format("{\"total\":%d,\"successes\":%d,\"rate\":%.2f}", total, successes, successRate));
            event.setSuggestedActions("1. 立即检查算法服务状态\n2. 重启算法服务\n3. 检查GPU资源是否充足\n4. 查看完整错误日志");
            events.add(event);
        }
    }

    // ============================================================
    // 3. 手势识别置信度持续偏低（5分钟均值 < 0.5）
    // ============================================================
    private void detectGestureConfidenceLow(List<AnomalyEvent> events) {
        LocalDateTime fiveMinutesAgo = LocalDateTime.now().minusMinutes(5);
        List<SystemLog> logs = findByModulesAndCreatedAtAfter(
                List.of("gesture", "owner_gesture", "police_gesture"),
                fiveMinutesAgo
        );

        if (logs.isEmpty()) return;

        List<Double> confidences = logs.stream()
                .map(this::extractConfidence)
                .filter(Objects::nonNull)
                .toList();

        if (confidences.isEmpty()) return;

        double avgConfidence = confidences.stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(lowConfidenceThreshold);

        if (avgConfidence < lowConfidenceThreshold) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.GESTURE_CONFIDENCE_LOW);
            event.setSeverity(AlertSeverity.WARNING);
            event.setTitle("手势识别置信度持续偏低");
            event.setSummary(String.format("过去5分钟内手势识别平均置信度 %.2f，低于 %.2f 阈值",
                    avgConfidence, lowConfidenceThreshold));
            event.setMetrics(String.format("{\"avgConfidence\":%.2f,\"sampleCount\":%d}",
                    avgConfidence, confidences.size()));
            event.setSuggestedActions("1. 检查摄像头画面是否清晰\n2. 调整手势识别参数\n3. 确认手部关键点检测是否正常");
            events.add(event);
        }
    }

    // ============================================================
    // 4. LLM API 超时（>30秒 或 1分钟 ≥3次）
    // ============================================================
    private void detectLlmTimeout(List<AnomalyEvent> events) {
        LocalDateTime oneMinuteAgo = LocalDateTime.now().minusMinutes(1);
        List<SystemLog> timeoutLogs = systemLogRepository.findByModuleAndEventAndCreatedAtAfter(
                "llm", "timeout", oneMinuteAgo);

        long timeoutCount = timeoutLogs.size();
        if (timeoutCount >= 3) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.LLM_TIMEOUT);
            event.setSeverity(AlertSeverity.WARNING);
            event.setTitle("LLM API 超时频繁");
            event.setSummary(String.format("过去1分钟内 LLM API 超时 %d 次，超过3次阈值", timeoutCount));
            event.setMetrics(String.format("{\"timeoutCount\":%d,\"windowSeconds\":60}", timeoutCount));
            event.setSuggestedActions("1. 检查网络连接\n2. 确认 LLM API Key 是否有效\n3. 切换到备用 LLM 服务");
            events.add(event);
        }
    }

    // ============================================================
    // 5. LLM Token 超额（80%/100% 阈值）
    // ============================================================
    private void detectLlmTokenExceeded(List<AnomalyEvent> events) {
        // 假设从日志中获取 Token 使用量
        // 这里简化实现，实际可以从数据库或监控系统获取
        LocalDateTime today = LocalDateTime.now().withHour(0).withMinute(0).withSecond(0);
        List<SystemLog> todayLogs = systemLogRepository.findByModuleAndCreatedAtAfter("llm", today);

        long totalTokens = todayLogs.stream()
                .mapToLong(this::extractTokenUsage)
                .sum();

        if (tokenLimit <= 0) return;

        double usage = (double) totalTokens / tokenLimit;

        if (usage >= 0.8) {
            AlertSeverity severity = usage >= 1.0 ? AlertSeverity.CRITICAL : AlertSeverity.WARNING;
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.LLM_TOKEN_EXCEEDED);
            event.setSeverity(severity);
            event.setTitle(usage >= 1.0 ? "LLM Token 已用完" : "LLM Token 接近限额");
            event.setSummary(String.format("今日 LLM Token 使用量 %.1f%%（%d / %d）", usage * 100, totalTokens, tokenLimit));
            event.setMetrics(String.format("{\"used\":%d,\"quota\":%d,\"usage\":%.2f}", totalTokens, tokenLimit, usage));
            event.setSuggestedActions("1. 减少不必要的 LLM 调用\n2. 优化 Prompt 减少 Token 消耗\n3. 联系管理员增加配额");
            events.add(event);
        }
    }

    // ============================================================
    // 6. 未授权访问
    // ============================================================
    private void detectUnauthorizedAccess(List<AnomalyEvent> events) {
        LocalDateTime fiveMinutesAgo = LocalDateTime.now().minusMinutes(5);
        List<SystemLog> authFailLogs = systemLogRepository.findByModuleAndEventAndCreatedAtAfter(
                "auth", "unauthorized", fiveMinutesAgo);

        if (!authFailLogs.isEmpty()) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.UNAUTHORIZED_ACCESS);
            event.setSeverity(AlertSeverity.CRITICAL);
            event.setTitle("检测到未授权访问");
            event.setSummary(String.format("过去5分钟内检测到 %d 次未授权访问尝试", authFailLogs.size()));
            event.setMetrics(String.format("{\"attempts\":%d,\"windowMinutes\":5}", authFailLogs.size()));
            event.setSuggestedActions("1. 检查是否有恶意攻击\n2. 确认认证配置是否正确\n3. 查看访问来源IP\n4. 考虑临时封禁IP");
            events.add(event);
        }
    }

    // ============================================================
    // 7. 数据库连接失败
    // ============================================================
    private void detectDatabaseConnectionFailure(List<AnomalyEvent> events) {
        LocalDateTime oneMinuteAgo = LocalDateTime.now().minusMinutes(1);
        List<SystemLog> dbErrorLogs = systemLogRepository.findByModuleAndEventAndCreatedAtAfter(
                "database", "connection_error", oneMinuteAgo);

        if (!dbErrorLogs.isEmpty()) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.DATABASE_CONNECTION_FAILURE);
            event.setSeverity(AlertSeverity.CRITICAL);
            event.setTitle("数据库连接失败");
            event.setSummary("检测到数据库连接异常，可能影响数据读写");
            event.setMetrics(String.format("{\"errorCount\":%d,\"lastError\":\"%s\"}",
                    dbErrorLogs.size(), dbErrorLogs.get(0).getDetail()));
            event.setSuggestedActions("1. 检查数据库服务是否运行\n2. 检查数据库连接配置\n3. 检查网络连接\n4. 重启数据库服务");
            events.add(event);
        }
    }

    // ============================================================
    // 8. 系统资源过高（CPU/内存）
    // ============================================================
    private void detectSystemResourceHigh(List<AnomalyEvent> events) {
        // 获取系统资源使用率
        double cpuUsage = getCpuUsage();
        double memoryUsage = getMemoryUsage();

        if (cpuUsage > 80 || memoryUsage > 80) {
            AnomalyEvent event = new AnomalyEvent();
            event.setType(AnomalyType.SYSTEM_RESOURCE_HIGH);
            event.setSeverity(cpuUsage > 90 || memoryUsage > 90 ? AlertSeverity.CRITICAL : AlertSeverity.WARNING);

            String resource = cpuUsage > 80 ? "CPU" : "内存";
            double usage = cpuUsage > 80 ? cpuUsage : memoryUsage;
            event.setTitle(String.format("系统%s使用率过高", resource));
            event.setSummary(String.format("当前系统%s使用率 %.1f%%，超过80%%阈值", resource, usage));
            event.setMetrics(String.format("{\"cpu\":%.2f,\"memory\":%.2f}", cpuUsage, memoryUsage));
            event.setSuggestedActions("1. 检查是否有大量请求积压\n2. 考虑扩容或限流\n3. 检查是否有内存泄漏\n4. 重启服务释放资源");
            events.add(event);
        }
    }

    // ============================================================
    // 辅助方法
    // ============================================================

    private double getCpuUsage() {
        java.lang.management.OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
        double loadAverage = osBean.getSystemLoadAverage();
        if (loadAverage < 0) {
            return 0;
        }
        return Math.min(100, (loadAverage / osBean.getAvailableProcessors()) * 100);
    }

    private double getMemoryUsage() {
        // 简化实现：返回模拟值
        // 实际可以使用 Runtime.getRuntime()
        Runtime runtime = Runtime.getRuntime();
        long usedMemory = runtime.totalMemory() - runtime.freeMemory();
        long maxMemory = runtime.maxMemory();
        return (double) usedMemory / maxMemory * 100;
    }

    private List<SystemLog> findByModulesAndCreatedAtAfter(Collection<String> modules, LocalDateTime after) {
        List<SystemLog> logs = new ArrayList<>();
        for (String module : modules) {
            logs.addAll(systemLogRepository.findByModuleAndCreatedAtAfter(module, after));
        }
        return logs;
    }

    private Double extractConfidence(SystemLog log) {
        String detail = log.getDetail();
        if (detail == null || detail.isBlank()) {
            return null;
        }

        Double numericDetail = parseDouble(detail);
        if (numericDetail != null) {
            return numericDetail;
        }

        try {
            JsonNode node = objectMapper.readTree(detail);
            for (String field : List.of("confidence", "avgConfidence", "ocrConfidence", "detectionConfidence")) {
                JsonNode value = node.get(field);
                if (value != null && value.isNumber()) {
                    return value.asDouble();
                }
            }
        } catch (Exception ignored) {
            return null;
        }
        return null;
    }

    private long extractTokenUsage(SystemLog log) {
        String detail = log.getDetail();
        if (detail == null || detail.isBlank()) {
            return 0;
        }

        try {
            return Long.parseLong(detail);
        } catch (NumberFormatException ignored) {
            // 继续尝试 JSON 解析
        }

        try {
            JsonNode node = objectMapper.readTree(detail);
            for (String field : List.of("tokens", "totalTokens", "tokenUsage", "total_tokens")) {
                JsonNode value = node.get(field);
                if (value != null && value.canConvertToLong()) {
                    return value.asLong();
                }
            }
        } catch (Exception ignored) {
            return 0;
        }
        return 0;
    }

    private Double parseDouble(String value) {
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
