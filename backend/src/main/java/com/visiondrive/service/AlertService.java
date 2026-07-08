package com.visiondrive.service;

import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.repository.AlertEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class AlertService {

    private final AlertEventRepository alertEventRepository;

    /**
     * 获取告警列表
     */
    public List<AlertEvent> getAlertList(String severity, Boolean resolved) {
        if (severity != null && resolved != null) {
            return alertEventRepository.findBySeverityAndResolved(severity, resolved);
        } else if (severity != null) {
            return alertEventRepository.findBySeverity(severity);
        } else if (resolved != null) {
            return alertEventRepository.findByResolved(resolved);
        } else {
            return alertEventRepository.findAll();
        }
    }

    /**
     * 获取告警统计数据
     */
    public Map<String, Object> getAlertStats() {
        Map<String, Object> stats = new HashMap<>();

        // 总数
        long total = alertEventRepository.count();
        stats.put("total", total);

        // 按级别统计
        long infoCount = alertEventRepository.countBySeverity("info");
        long warningCount = alertEventRepository.countBySeverity("warning");
        long criticalCount = alertEventRepository.countBySeverity("critical");

        Map<String, Long> bySeverity = new HashMap<>();
        bySeverity.put("info", infoCount);
        bySeverity.put("warning", warningCount);
        bySeverity.put("critical", criticalCount);
        stats.put("bySeverity", bySeverity);

        // 未处理数量
        long unresolved = alertEventRepository.countByResolved(false);
        stats.put("unresolved", unresolved);

        // 已处理数量
        long resolved = alertEventRepository.countByResolved(true);
        stats.put("resolved", resolved);

        return stats;
    }
}