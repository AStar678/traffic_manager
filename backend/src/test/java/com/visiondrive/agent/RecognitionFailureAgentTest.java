package com.visiondrive.agent;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertFalse;

class RecognitionFailureAgentTest {

    @Test
    void skipsReviewWhenDashscopeIsNotConfigured() {
        QwenVisionReviewer reviewer = new QwenVisionReviewer(null, null);
        ReflectionTestUtils.setField(reviewer, "apiKey", "");
        RecognitionFailureAgent agent = new RecognitionFailureAgent(
                reviewer,
                null,
                null
        );
        ReflectionTestUtils.setField(agent, "enabled", true);

        try {
            assertFalse(agent.submitIfNeeded(
                    "police_gesture",
                    "/tmp/failure.jpg",
                    0.1,
                    "低置信度",
                    "trace-1"
            ));
        } finally {
            agent.shutdown();
        }
    }
}
