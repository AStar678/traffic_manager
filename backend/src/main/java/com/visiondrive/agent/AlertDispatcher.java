package com.visiondrive.agent;

import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.repository.AlertEventRepository;
import com.visiondrive.websocket.AlertWebSocketHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class AlertDispatcher {

    private final AlertEventRepository alertEventRepository;
    private final AlertWebSocketHandler webSocketHandler;
    private final LlmSummarizer llmSummarizer;

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
        summary.put("id", saved.getId());
        summary.put("createdAt", saved.getCreatedAt().toString());

        webSocketHandler.pushAlertToAllClients(summary);

        // 4. 邮件通知（仅严重告警）
        if ("critical".equals(summary.get("severity"))) {
            sendEmailNotification(summary);
        }

        // 5. Webhook 通知（企业微信/钉钉/飞书）
        sendWebhookNotification(summary);
    }

    /**
     * 发送邮件通知
     */
    private void sendEmailNotification(Map<String, Object> alert) {
        // TODO: 实现邮件发送
        log.info("📧 邮件通知: {} - {}", alert.get("severityLabel"), alert.get("title"));
    }

    /**
     * 发送 Webhook 通知
     */
    private void sendWebhookNotification(Map<String, Object> alert) {
        // TODO: 实现 Webhook 推送（企业微信/钉钉/飞书）
        log.info("🔔 Webhook 通知: {} - {}", alert.get("severityEmoji"), alert.get("title"));
    }
}