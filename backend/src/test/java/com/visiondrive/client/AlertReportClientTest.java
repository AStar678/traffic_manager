package com.visiondrive.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class AlertReportClientTest {

    private AlertReportClient client;
    private MockRestServiceServer server;

    @BeforeEach
    void setUp() {
        RestTemplate restTemplate = new RestTemplate();
        client = new AlertReportClient(restTemplate, new ObjectMapper());
        ReflectionTestUtils.setField(client, "enabled", true);
        ReflectionTestUtils.setField(client, "baseUrl", "http://alert-service:8096");
        ReflectionTestUtils.setField(client, "token", "test-alert-token");
        server = MockRestServiceServer.bindTo(restTemplate).build();
    }

    @Test
    void reportsCriticalAlertUsingMicroserviceContract() {
        server.expect(requestTo("http://alert-service:8096/api/alert/receive"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Alert-Token", "test-alert-token"))
                .andExpect(content().json("""
                        {
                          "alertId": "alert_test_001",
                          "severity": "critical",
                          "title": "Agent 测试告警",
                          "summary": "测试摘要",
                          "anomalyType": "SYSTEM_RESOURCE_HIGH",
                          "affectedModule": "system",
                          "occurredAt": "2026-07-13T09:00:00",
                          "metrics": {"cpu": "95"},
                          "suggestedActions": ["检查进程", "释放资源"]
                        }
                        """))
                .andRespond(withSuccess("{\"code\":200,\"msg\":\"ok\"}", MediaType.APPLICATION_JSON));

        Map<String, Object> alert = new LinkedHashMap<>();
        alert.put("alertId", "alert_test_001");
        alert.put("severity", "critical");
        alert.put("title", "Agent 测试告警");
        alert.put("summary", "测试摘要");
        alert.put("anomalyType", "SYSTEM_RESOURCE_HIGH");
        alert.put("affectedModule", "system");
        alert.put("occurredAt", "2026-07-13T09:00:00");
        alert.put("metrics", "{\"cpu\":95}");
        alert.put("suggestedActions", "1. 检查进程\n2. 释放资源");

        assertTrue(client.report(alert));
        server.verify();
    }
}
