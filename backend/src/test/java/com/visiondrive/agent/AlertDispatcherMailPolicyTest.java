package com.visiondrive.agent;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AlertDispatcherMailPolicyTest {

    private final AlertDispatcher dispatcher = new AlertDispatcher(null, null, null, null);

    @Test
    void reportsRecognitionReviewWarningToMailService() {
        Map<String, Object> alert = Map.of(
                "severity", "warning",
                "anomalyType", AnomalyType.RECOGNITION_FAILURE_REVIEW.name(),
                "affectedModule", "license_plate"
        );

        Boolean shouldReport = ReflectionTestUtils.invokeMethod(
                dispatcher,
                "shouldReportToMailService",
                alert
        );

        assertTrue(Boolean.TRUE.equals(shouldReport));
    }

    @Test
    void doesNotReportOrdinaryWarningsToMailService() {
        Map<String, Object> alert = Map.of(
                "severity", "warning",
                "anomalyType", AnomalyType.GESTURE_CONFIDENCE_LOW.name(),
                "affectedModule", "gesture"
        );

        Boolean shouldReport = ReflectionTestUtils.invokeMethod(
                dispatcher,
                "shouldReportToMailService",
                alert
        );

        assertFalse(Boolean.TRUE.equals(shouldReport));
    }
}
