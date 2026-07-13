package com.visiondrive.agent;

import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.repository.SystemLogRepository;
import com.visiondrive.service.SystemLogService;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.lang.reflect.Proxy;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LlmSummarizerTest {

    @Test
    void keepsVisionReviewSummaryWithoutSecondLlmRewrite() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        SystemLogRepository repository = (SystemLogRepository) Proxy.newProxyInstance(
                SystemLogRepository.class.getClassLoader(),
                new Class<?>[]{SystemLogRepository.class},
                (proxy, method, args) -> "save".equals(method.getName()) ? (SystemLog) args[0] : null
        );
        LlmSummarizer summarizer = new LlmSummarizer(
                restTemplate,
                new SystemLogService(repository)
        );
        ReflectionTestUtils.setField(summarizer, "apiKey", "test-dashscope-key");
        ReflectionTestUtils.setField(summarizer, "model", "qwen-plus");
        ReflectionTestUtils.setField(summarizer, "baseUrl", "https://dashscope.example/compatible-mode/v1");

        AnomalyEvent event = new AnomalyEvent();
        event.setType(AnomalyType.RECOGNITION_FAILURE_REVIEW);
        event.setSeverity(AlertSeverity.WARNING);
        event.setAffectedModule("license_plate");
        event.setTitle("车牌识别失败样本已完成 Agent 复核");
        event.setSummary("复核结果：画面中车牌被强反光遮挡。可能根因：曝光过高、角度偏斜。建议处置：调整摄像头角度并加入困难样本。");
        event.setMetrics("{}");
        event.setSuggestedActions("在错误日志中回放失败样本");

        Map<String, Object> summary = summarizer.generateSummary(event);

        assertEquals(event.getSummary(), summary.get("summary"));
        server.verify();
    }
}
