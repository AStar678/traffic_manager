package com.alert.util;

import com.alert.dto.AlertMailDTO;
import jakarta.mail.internet.MimeMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.StringJoiner;

@Component
public class AlertMailUtil {

    private static final Logger log = LoggerFactory.getLogger(AlertMailUtil.class);
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String RECOGNITION_REVIEW = "RECOGNITION_FAILURE_REVIEW";

    private final JavaMailSender javaMailSender;

    @Value("${alert.email.recipients:}")
    private String recipients;

    @Value("${alert.email.from:}")
    private String mailFrom;

    @Value("${alert.email.enabled:true}")
    private boolean mailEnable;

    public AlertMailUtil(JavaMailSender javaMailSender) {
        this.javaMailSender = javaMailSender;
    }

    public boolean sendEmailNotification(AlertMailDTO alert) {
        if (!mailEnable) {
            log.info("告警邮件功能已关闭，跳过发送");
            return false;
        }
        if (!shouldSend(alert)) {
            log.info("告警未达到邮件发送条件，跳过: alertId={}, severity={}, anomalyType={}",
                    alert.getAlertId(), alert.getSeverity(), alert.getAnomalyType());
            return false;
        }

        try {
            MimeMessage message = javaMailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(mailFrom);
            helper.setTo(resolveRecipients());
            helper.setSubject("%s %s".formatted(subjectPrefix(alert), safe(alert.getTitle(), "系统告警")));
            helper.setText(buildHtml(alert), true);
            javaMailSender.send(message);
            log.info("告警邮件推送完成，告警ID={}，级别={}，收件人={}",
                    alert.getAlertId(), alert.getSeverity(), recipients);
            return true;
        } catch (Exception error) {
            log.error("告警邮件发送失败，告警ID={}", alert.getAlertId(), error);
            return false;
        }
    }

    private boolean shouldSend(AlertMailDTO alert) {
        if ("critical".equalsIgnoreCase(alert.getSeverity())) {
            return true;
        }
        if (!"warning".equalsIgnoreCase(alert.getSeverity())) {
            return false;
        }
        if (!RECOGNITION_REVIEW.equals(alert.getAnomalyType())) {
            return false;
        }
        String module = safe(alert.getAffectedModule(), "");
        return "license_plate".equals(module) || "police_gesture".equals(module);
    }

    private String[] resolveRecipients() {
        return Arrays.stream(safe(recipients, "").split(","))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .toArray(String[]::new);
    }

    private String subjectPrefix(AlertMailDTO alert) {
        if ("critical".equalsIgnoreCase(alert.getSeverity())) {
            return "🔴 [严重告警]";
        }
        if (RECOGNITION_REVIEW.equals(alert.getAnomalyType())) {
            return "⚠️ [识别复核告警]";
        }
        if ("warning".equalsIgnoreCase(alert.getSeverity())) {
            return "⚠️ [警告]";
        }
        return "💡 [提示]";
    }

    private String buildHtml(AlertMailDTO alert) {
        String metricsHtml = metricsHtml(alert.getMetrics());
        String actionsHtml = actionsHtml(alert.getSuggestedActions());
        String summaryHtml = isBlank(alert.getSummary())
                ? ""
                : """
                  <hr/>
                  <p><strong>🧠 Agent复核结论：</strong><br/>%s</p>
                  """.formatted(escape(alert.getSummary()).replace("\n", "<br/>"));

        return """
                <div style="font-size:15px;line-height:1.7">
                    <h3>【VisionDrive 系统告警通知】</h3>
                    <p>告警ID：%s</p>
                    <p>告警级别：%s</p>
                    <p>告警标题：%s</p>
                    <p>异常类型：%s</p>
                    <p>影响模块：%s</p>
                    <p>发生时间：%s</p>
                    %s
                    <hr/>
                    <p>📊 详细指标：<br/>%s</p>
                    <hr/>
                    <p>💡 建议措施：<br/>%s</p>
                    <hr/>
                    <p style="color:#777;font-size:13px">此邮件由 VisionDrive 告警智能体自动发送，请勿回复。<br/>如需取消此类通知，请联系系统管理员。</p>
                </div>
                """.formatted(
                escape(alert.getAlertId()),
                escape(severityLabel(alert)),
                escape(safe(alert.getTitle(), "系统告警")),
                escape(safe(alert.getAnomalyType(), "UNKNOWN")),
                escape(safe(alert.getAffectedModule(), "unknown")),
                formatTime(alert.getOccurredAt()),
                summaryHtml,
                metricsHtml,
                actionsHtml
        );
    }

    private String severityLabel(AlertMailDTO alert) {
        if ("critical".equalsIgnoreCase(alert.getSeverity())) {
            return "🔴 严重";
        }
        if ("warning".equalsIgnoreCase(alert.getSeverity())) {
            return "⚠️ 警告";
        }
        return "💡 提示";
    }

    private String metricsHtml(Map<String, Object> metrics) {
        if (metrics == null || metrics.isEmpty()) {
            return "无";
        }
        StringJoiner joiner = new StringJoiner("<br/>");
        metrics.forEach((key, value) -> joiner.add("- %s：%s".formatted(
                escape(key),
                escape(Objects.toString(value, ""))
        )));
        return joiner.toString();
    }

    private String actionsHtml(List<String> suggestedActions) {
        if (suggestedActions == null || suggestedActions.isEmpty()) {
            return "请联系系统管理员检查。";
        }
        StringJoiner joiner = new StringJoiner("<br/>");
        int index = 1;
        for (String action : suggestedActions) {
            joiner.add("%d. %s".formatted(index++, escape(action)));
        }
        return joiner.toString();
    }

    private String formatTime(LocalDateTime occurredAt) {
        return (occurredAt == null ? LocalDateTime.now() : occurredAt).format(FORMATTER);
    }

    private String safe(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private String escape(String value) {
        return safe(value, "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;");
    }
}
