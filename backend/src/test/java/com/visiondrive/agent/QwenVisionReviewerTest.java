package com.visiondrive.agent;

import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.repository.SystemLogRepository;
import com.visiondrive.service.SystemLogService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.lang.reflect.Proxy;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class QwenVisionReviewerTest {

    @Test
    void sendsFailedVideoToQwenVisionModel() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        SystemLogRepository repository = (SystemLogRepository) Proxy.newProxyInstance(
                SystemLogRepository.class.getClassLoader(),
                new Class<?>[]{SystemLogRepository.class},
                (proxy, method, args) -> "save".equals(method.getName()) ? (SystemLog) args[0] : null
        );
        QwenVisionReviewer reviewer = new QwenVisionReviewer(
                restTemplate,
                new SystemLogService(repository)
        );
        ReflectionTestUtils.setField(reviewer, "apiKey", "test-dashscope-key");
        ReflectionTestUtils.setField(reviewer, "visionModel", "qwen-vl-plus");
        ReflectionTestUtils.setField(reviewer, "baseUrl", "https://dashscope.example/compatible-mode/v1");
        ReflectionTestUtils.setField(reviewer, "maxBase64Bytes", 7_340_032L);
        ReflectionTestUtils.setField(reviewer, "uploadDir", "./uploads");
        ReflectionTestUtils.setField(reviewer, "publicBaseUrl", "");

        server.expect(requestTo("https://dashscope.example/compatible-mode/v1/chat/completions"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("Authorization", "Bearer test-dashscope-key"))
                .andExpect(jsonPath("$.model").value("qwen-vl-plus"))
                .andExpect(jsonPath("$.messages[0].content[0].type").value("video_url"))
                .andExpect(jsonPath("$.messages[0].content[0].video_url.url")
                        .value("https://files.example/failure.mp4"))
                .andExpect(jsonPath("$.messages[0].content[0].fps").value(1))
                .andRespond(withSuccess("""
                        {
                          "choices": [{"message": {"content": "复核结果：画面存在交警，原模型可能受逆光影响。"}}],
                          "usage": {"total_tokens": 321}
                        }
                        """, MediaType.APPLICATION_JSON));

        QwenVisionReviewer.ReviewResult result = reviewer.review(
                "police_gesture",
                "https://files.example/failure.mp4",
                0.31,
                "置信度低于阈值"
        );

        assertEquals("复核结果：画面存在交警，原模型可能受逆光影响。", result.analysis());
        assertEquals(321, result.tokens());
        server.verify();
    }
}
