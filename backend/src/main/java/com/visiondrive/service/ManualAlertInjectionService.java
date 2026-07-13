package com.visiondrive.service;

import com.visiondrive.agent.AlertDispatcher;
import com.visiondrive.agent.AlertSeverity;
import com.visiondrive.agent.AnomalyEvent;
import com.visiondrive.agent.AnomalyType;
import com.visiondrive.common.utils.JsonLogBuilder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ManualAlertInjectionService {

    private final SystemLogService systemLogService;
    private final AlertDispatcher alertDispatcher;

    public Map<String, Object> injectDatabaseConnectionFailure() {
        String injectionId = "manual_db_failure_" + UUID.randomUUID();
        String jdbcUrl = "jdbc:h2:mem:" + injectionId + ";IFEXISTS=TRUE";
        long startAt = System.currentTimeMillis();
        SQLException failure = executeGuaranteedFailedConnection(jdbcUrl);
        long latencyMs = System.currentTimeMillis() - startAt;

        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("injectionId", injectionId);
        detail.put("trigger", "manual_button");
        detail.put("jdbcUrl", jdbcUrl);
        detail.put("latencyMs", latencyMs);
        detail.put("errorType", failure.getClass().getSimpleName());
        detail.put("errorMessage", failure.getMessage());

        systemLogService.error("database", "connection_error", detail);

        AnomalyEvent event = new AnomalyEvent();
        event.setType(AnomalyType.DATABASE_CONNECTION_FAILURE);
        event.setSeverity(AlertSeverity.CRITICAL);
        event.setAffectedModule("database");
        event.setTitle("手动注入：数据库连接失败严重告警");
        event.setSummary("用户手动触发数据库连接失败演练，系统已执行一次必定失败的 JDBC 连接尝试，并捕获异常生成严重告警。");
        event.setMetrics(JsonLogBuilder.toJson(detail));
        event.setSuggestedActions("1. 确认这是手动演练告警；2. 检查邮件微服务是否收到 critical 告警；3. 在错误日志中核对数据库 connection_error 记录。");

        alertDispatcher.dispatch(event);
        log.warn("手动数据库失败告警已注入: injectionId={}, latencyMs={}", injectionId, latencyMs);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("injectionId", injectionId);
        result.put("severity", "critical");
        result.put("module", "database");
        result.put("event", "connection_error");
        result.put("message", "数据库连接失败演练已注入，严重告警与邮件链路已触发");
        return result;
    }

    private SQLException executeGuaranteedFailedConnection(String jdbcUrl) {
        try (var ignored = DriverManager.getConnection(jdbcUrl, "visiondrive_manual_probe", "invalid_password")) {
            return new SQLException("手动演练数据库连接意外成功，已强制转为失败告警");
        } catch (SQLException error) {
            return error;
        }
    }
}
