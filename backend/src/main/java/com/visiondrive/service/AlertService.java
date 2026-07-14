package com.visiondrive.service;

import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.repository.AlertEventRepository;
import com.visiondrive.repository.SystemLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Service
@RequiredArgsConstructor
public class AlertService {

    private final AlertEventRepository alertEventRepository;
    private final SystemLogRepository systemLogRepository;

    /**
     * 获取告警列表
     */
    public List<AlertEvent> getAlertList(String severity, Boolean resolved) {
        String normalizedSeverity = severity == null ? null : severity.toLowerCase();
        return alertEventRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt")).stream()
                .filter(alert -> normalizedSeverity == null || normalizedSeverity.equals(alert.getSeverity()))
                .filter(alert -> resolved == null || Objects.equals(resolved, alert.getResolved()))
                .toList();
    }

    /**
     * 获取告警统计数据
     */
    public Map<String, Object> getAlertStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        List<AlertEvent> alerts = alertEventRepository.findAll();
        LocalDateTime todayStart = LocalDate.now().atStartOfDay();

        // 总数
        long total = alerts.size();
        stats.put("total", total);
        stats.put("totalToday", alerts.stream()
                .filter(alert -> alert.getCreatedAt() != null && !alert.getCreatedAt().isBefore(todayStart))
                .count());

        // 按级别统计
        long infoCount = countSeverity(alerts, "info");
        long warningCount = countSeverity(alerts, "warning");
        long criticalCount = countSeverity(alerts, "critical");

        Map<String, Long> bySeverity = new LinkedHashMap<>();
        bySeverity.put("info", infoCount);
        bySeverity.put("warning", warningCount);
        bySeverity.put("critical", criticalCount);
        stats.put("bySeverity", bySeverity);
        stats.put("info", infoCount);
        stats.put("warning", warningCount);
        stats.put("critical", criticalCount);
        stats.put("severity", List.of(
                Map.of("name", "提示", "value", infoCount),
                Map.of("name", "警告", "value", warningCount),
                Map.of("name", "严重", "value", criticalCount)
        ));
        stats.put("trend", buildSevenDayTrend(alerts));
        stats.put("modules", buildModuleStats(alerts));

        // 未处理数量
        long unresolved = alerts.stream().filter(alert -> Boolean.FALSE.equals(alert.getResolved())).count();
        stats.put("unresolved", unresolved);

        // 已处理数量
        long resolved = alerts.stream().filter(alert -> Boolean.TRUE.equals(alert.getResolved())).count();
        stats.put("resolved", resolved);

        return stats;
    }

    public AlertEvent getAlertDetail(Long id) {
        return alertEventRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("告警不存在: " + id));
    }

    public AlertEvent updateAlertStatus(Long id, String status) {
        AlertEvent alert = getAlertDetail(id);
        boolean resolved = "resolved".equalsIgnoreCase(status) || "true".equalsIgnoreCase(status);
        alert.setResolved(resolved);
        alert.setResolvedAt(resolved ? LocalDateTime.now() : null);
        return alertEventRepository.save(alert);
    }

    public List<SystemLog> getSystemLogs(String module, String event, String level, Integer limit) {
        int safeLimit = limit == null || limit <= 0 ? 100 : Math.min(limit, 500);
        return systemLogRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt")).stream()
                .filter(log -> module == null || module.equals(log.getModule()))
                .filter(log -> event == null || event.equals(log.getEvent()))
                .filter(log -> level == null || level.equalsIgnoreCase(log.getLevel()))
                .limit(safeLimit)
                .toList();
    }

    @Transactional
    public int clearErrorLogs(String module, String event) {
        return systemLogRepository.deleteErrorLogs(normalizeFilter(module), normalizeFilter(event));
    }

    private String normalizeFilter(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private long countSeverity(List<AlertEvent> alerts, String severity) {
        return alerts.stream().filter(alert -> severity.equals(alert.getSeverity())).count();
    }

    private List<Long> buildSevenDayTrend(List<AlertEvent> alerts) {
        List<Long> trend = new ArrayList<>();
        LocalDate start = LocalDate.now().minusDays(6);
        for (int i = 0; i < 7; i++) {
            LocalDate day = start.plusDays(i);
            long count = alerts.stream()
                    .filter(alert -> alert.getCreatedAt() != null)
                    .filter(alert -> alert.getCreatedAt().toLocalDate().equals(day))
                    .count();
            trend.add(count);
        }
        return trend;
    }

    private List<Map<String, Object>> buildModuleStats(List<AlertEvent> alerts) {
        Map<String, Long> moduleCounts = new LinkedHashMap<>();
        for (AlertEvent alert : alerts) {
            String module = alert.getAffectedModule() == null ? "unknown" : alert.getAffectedModule();
            moduleCounts.put(module, moduleCounts.getOrDefault(module, 0L) + 1);
        }
        return moduleCounts.entrySet().stream()
                .map(entry -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("name", entry.getKey());
                    item.put("value", entry.getValue());
                    return item;
                })
                .toList();
    }
}
