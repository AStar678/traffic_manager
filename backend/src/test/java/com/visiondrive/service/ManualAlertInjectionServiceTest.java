package com.visiondrive.service;

import com.visiondrive.agent.AlertDispatcher;
import com.visiondrive.agent.AlertSeverity;
import com.visiondrive.agent.AnomalyEvent;
import com.visiondrive.agent.AnomalyType;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ManualAlertInjectionServiceTest {

    @Test
    void injectsCriticalDatabaseConnectionFailureAlert() {
        CapturingSystemLogService systemLogService = new CapturingSystemLogService();
        CapturingAlertDispatcher alertDispatcher = new CapturingAlertDispatcher();
        ManualAlertInjectionService service = new ManualAlertInjectionService(systemLogService, alertDispatcher);

        Map<String, Object> result = service.injectDatabaseConnectionFailure();

        assertEquals("database", systemLogService.module);
        assertEquals("connection_error", systemLogService.event);
        assertTrue(systemLogService.detail.containsKey("errorMessage"));

        AnomalyEvent event = alertDispatcher.event;
        assertNotNull(event);
        assertEquals(AnomalyType.DATABASE_CONNECTION_FAILURE, event.getType());
        assertEquals(AlertSeverity.CRITICAL, event.getSeverity());
        assertEquals("database", event.getAffectedModule());
        assertTrue(event.getMetrics().contains("manual_db_failure_"));

        assertEquals("critical", result.get("severity"));
        assertEquals("database", result.get("module"));
        assertEquals("connection_error", result.get("event"));
    }

    private static class CapturingSystemLogService extends SystemLogService {
        private String module;
        private String event;
        private Map<String, Object> detail = new LinkedHashMap<>();

        private CapturingSystemLogService() {
            super(null);
        }

        @Override
        public void error(String module, String event, Map<String, Object> detail) {
            this.module = module;
            this.event = event;
            this.detail = detail;
        }
    }

    private static class CapturingAlertDispatcher extends AlertDispatcher {
        private AnomalyEvent event;

        private CapturingAlertDispatcher() {
            super(null, null, null, null);
        }

        @Override
        public void dispatch(AnomalyEvent event) {
            this.event = event;
        }
    }
}
