package com.alert.controller;

import com.alert.dto.AlertMailDTO;
import com.alert.util.AlertMailUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class AlertController {

    private static final Logger log = LoggerFactory.getLogger(AlertController.class);

    private final AlertMailUtil alertMailUtil;

    @Value("${alert.api.token:}")
    private String validToken;

    public AlertController(AlertMailUtil alertMailUtil) {
        this.alertMailUtil = alertMailUtil;
    }

    @PostMapping("/api/alert/receive")
    public ResponseEntity<?> receiveAlert(
            @RequestHeader(value = "X-Alert-Token", required = false) String token,
            @RequestBody AlertMailDTO alert
    ) {
        if (validToken == null || validToken.isBlank() || !validToken.equals(token)) {
            log.warn("非法调用告警接口，token无效");
            return ResponseEntity.status(403).body(Map.of("code", 403, "msg", "Token无效，禁止访问"));
        }
        if (alert == null || alert.getAlertId() == null || alert.getAlertId().isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("code", 400, "msg", "告警数据不能为空"));
        }

        boolean sent = alertMailUtil.sendEmailNotification(alert);
        return ResponseEntity.ok(Map.of(
                "code", 200,
                "msg", sent ? "告警接收成功，已执行邮件推送" : "告警接收成功，未达到邮件发送条件",
                "mailSent", sent
        ));
    }
}
