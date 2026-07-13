package com.visiondrive.agent;

import com.visiondrive.client.AlertReportClient;
import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.repository.AlertEventRepository;
import com.visiondrive.websocket.AlertWebSocketHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class AlertDispatcher {

    private final AlertEventRepository alertEventRepository;
    private final AlertWebSocketHandler webSocketHandler;
    private final LlmSummarizer llmSummarizer;
    private final AlertReportClient alertReportClient;

    /**
     * 分发告警
     */
    public void dispatch(AnomalyEvent event) {
        // 1. 生成告警摘要
        Map<String, Object> summary = llmSummarizer.generateSummary(event);

        // 2. 保存到数据库
        AlertEvent alertEvent = new AlertEvent();
        alertEvent.setAlertId((String) summary.get("alertId"));
        alertEvent.setSeverity((String) summary.get("severity"));
        alertEvent.setTitle((String) summary.get("title"));
        alertEvent.setSummary((String) summary.get("summary"));
        alertEvent.setAnomalyType((String) summary.get("anomalyType"));
        alertEvent.setAffectedModule((String) summary.get("affectedModule"));
        alertEvent.setMetrics((String) summary.get("metrics"));
        alertEvent.setSuggestedActions((String) summary.get("suggestedActions"));
        alertEvent.setResolved(false);
        alertEvent.setCreatedAt(LocalDateTime.now());

        AlertEvent saved = alertEventRepository.save(alertEvent);
        log.info("告警已保存: {}", saved.getAlertId());

        // 3. WebSocket 推送
        summary.put("type", "alert");
        summary.put("id", saved.getId());
        summary.put("createdAt", saved.getCreatedAt().toString());
        summary.put("module", saved.getAffectedModule());
        summary.put("status", saved.getResolved() ? "resolved" : "open");

        webSocketHandler.pushAlertToAllClients(summary);

        // 4. 需要邮件通知的告警上报独立微服务，由微服务完成邮件发送。
        if (shouldReportToMailService(summary)) {
            try {
                alertReportClient.report(summary);
            } catch (Exception error) {
                // 告警持久化和 WebSocket 推送已经完成，邮件链路失败不能回滚主体告警。
                log.error("告警邮件微服务上报失败: alertId={}, error={}",
                        summary.get("alertId"), error.getMessage());
            }
        }
    }

    private boolean shouldReportToMailService(Map<String, Object> alert) {
        if ("critical".equalsIgnoreCase(String.valueOf(alert.get("severity")))) {
            return true;
        }
        if (!AnomalyType.RECOGNITION_FAILURE_REVIEW.name().equals(String.valueOf(alert.get("anomalyType")))) {
            return false;
        }
        String module = String.valueOf(alert.get("affectedModule"));
        return "license_plate".equals(module) || "police_gesture".equals(module);
    }
}
