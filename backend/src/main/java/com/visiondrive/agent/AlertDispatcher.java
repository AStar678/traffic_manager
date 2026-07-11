package com.visiondrive.agent;

import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.repository.AlertEventRepository;
import com.visiondrive.websocket.AlertWebSocketHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Component
@RequiredArgsConstructor
public class AlertDispatcher {

    private final AlertEventRepository alertEventRepository;
    private final AlertWebSocketHandler webSocketHandler;
    private final LlmSummarizer llmSummarizer;
    private final JavaMailSender mailSender;

    @Value("${alert.email.enabled:true}")
    private boolean emailEnabled;

    @Value("${alert.email.recipients:}")
    private String emailRecipients;

    @Value("${alert.email.from:}")
    private String emailFrom;

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

        // 4. 邮件通知（警告及严重告警）
        if (shouldSendEmail(summary)) {
            sendEmailNotification(summary);
        }

    }

    /**
     * 发送邮件通知
     */
    private void sendEmailNotification(Map<String, Object> alert) {
        if (!emailEnabled) {
            log.debug("邮件告警已关闭，跳过发送: {}", alert.get("title"));
            return;
        }

        String[] recipients = parseRecipients();
        if (recipients.length == 0) {
            log.warn("邮件告警未配置收件人，跳过发送: {}", alert.get("title"));
            return;
        }

        try {
            SimpleMailMessage message = new SimpleMailMessage();
            if (emailFrom != null && !emailFrom.isBlank()) {
                message.setFrom(emailFrom);
            }
            message.setTo(recipients);
            message.setSubject(String.format("[VisionDrive][%s] %s",
                    Objects.toString(alert.get("severityLabel"), "告警"),
                    Objects.toString(alert.get("title"), "系统告警")));
            message.setText(buildEmailBody(alert));
            mailSender.send(message);
            log.info("邮件告警已发送: recipients={}, alertId={}", recipients.length, alert.get("alertId"));
        } catch (Exception e) {
            log.error("邮件告警发送失败: alertId={}, error={}", alert.get("alertId"), e.getMessage());
        }
    }

    private boolean shouldSendEmail(Map<String, Object> alert) {
        String severity = Objects.toString(alert.get("severity"), "");
        return "warning".equals(severity) || "critical".equals(severity);
    }

    private String[] parseRecipients() {
        if (emailRecipients == null || emailRecipients.isBlank()) {
            return new String[0];
        }
        return Arrays.stream(emailRecipients.split("[,;]"))
                .map(String::trim)
                .filter(item -> !item.isBlank())
                .toArray(String[]::new);
    }

    private String buildEmailBody(Map<String, Object> alert) {
        return """
                VisionDrive 监控告警

                告警ID：%s
                告警级别：%s
                异常类型：%s
                影响模块：%s
                发生时间：%s

                摘要：
                %s

                指标：
                %s

                建议处置：
                %s
                """.formatted(
                alert.get("alertId"),
                alert.get("severityLabel"),
                alert.get("anomalyType"),
                alert.get("affectedModule"),
                alert.get("occurredAt"),
                alert.get("summary"),
                alert.get("metrics"),
                alert.get("suggestedActions")
        );
    }
}
