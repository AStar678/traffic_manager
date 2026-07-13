package com.visiondrive.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class AlgorithmClientTest {

    private AlgorithmClient client;
    private MockRestServiceServer server;

    @BeforeEach
    void setUp() {
        RestTemplate restTemplate = new RestTemplate();
        client = new AlgorithmClient(restTemplate, new ObjectMapper());
        ReflectionTestUtils.setField(client, "licenseAlgorithmBaseUrl", "http://license:8000");
        ReflectionTestUtils.setField(client, "policeAlgorithmBaseUrl", "http://police:8001");
        ReflectionTestUtils.setField(client, "gestureAlgorithmBaseUrl", "http://gesture:8002");
        ReflectionTestUtils.setField(client, "vehicleAlgorithmBaseUrl", "http://vehicle:8004");
        ReflectionTestUtils.setField(client, "inferencePath", "/api/v1/inference/image");
        server = MockRestServiceServer.bindTo(restTemplate).build();
    }

    @Test
    void routesImageInferenceToIndependentServices() {
        server.expect(requestTo("http://license:8000/api/v1/inference/image"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(response("license_plate"), MediaType.APPLICATION_JSON));
        server.expect(requestTo("http://police:8001/api/v1/inference/image"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(response("police_gesture"), MediaType.APPLICATION_JSON));
        server.expect(requestTo("http://vehicle:8004/api/v1/inference/image"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess(response("vehicle_type"), MediaType.APPLICATION_JSON));

        assertEquals("license_plate", client.callImageInference("license_plate", "data:image/png;base64,AA==")
                .getData().getTaskType());
        assertEquals("police_gesture", client.callImageInference("police_gesture", "data:image/png;base64,AA==")
                .getData().getTaskType());
        assertEquals("vehicle_type", client.callImageInference("vehicle_type", "data:image/png;base64,AA==")
                .getData().getTaskType());
        server.verify();
    }

    @Test
    void rejectsUnsupportedImageTaskBeforeSendingHttpRequest() {
        assertThrows(
                IllegalArgumentException.class,
                () -> client.callImageInference("owner_gesture", "data:image/png;base64,AA==")
        );
        server.verify();
    }

    @Test
    void sendsCameraSourceIdForStatefulPoliceInference() {
        server.expect(requestTo("http://police:8001/api/v1/inference/image"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {
                          "task_type": "police_gesture",
                          "image_path": "/tmp/camera-2.jpg",
                          "source_id": "camera-slot-2"
                        }
                        """))
                .andRespond(withSuccess(response("police_gesture"), MediaType.APPLICATION_JSON));

        assertEquals("police_gesture", client.callFileInference(
                "police_gesture", "/tmp/camera-2.jpg", "camera-slot-2"
        ).getData().getTaskType());
        server.verify();
    }

    @Test
    void requestsPoliceKeypointsForDetailInference() {
        server.expect(requestTo("http://police:8001/api/v1/inference/image"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {
                          "task_type": "police_gesture",
                          "image_path": "/tmp/camera-1.jpg",
                          "source_id": "camera-slot-1",
                          "include_visuals": true
                        }
                        """))
                .andRespond(withSuccess(response("police_gesture"), MediaType.APPLICATION_JSON));

        assertEquals("police_gesture", client.callFileInference(
                "police_gesture", "/tmp/camera-1.jpg", "camera-slot-1", true
        ).getData().getTaskType());
        server.verify();
    }

    @Test
    void activatesDinov2OwnerGestureAlgorithm() {
        server.expect(requestTo("http://gesture:8002/api/v1/owner-gestures/algorithm"))
                .andExpect(method(HttpMethod.PUT))
                .andExpect(content().json("""
                        {
                          "algorithm": "dinov2_tcn_prototype"
                        }
                        """))
                .andRespond(withSuccess("""
                        {
                          "algorithm": {
                            "active": "dinov2_tcn_prototype"
                          }
                        }
                        """, MediaType.APPLICATION_JSON));

        Map<String, Object> result = client.activateOwnerGestureAlgorithm();
        @SuppressWarnings("unchecked")
        Map<String, Object> algorithm = (Map<String, Object>) result.get("algorithm");
        assertEquals("dinov2_tcn_prototype", algorithm.get("active"));
        server.verify();
    }

    private String response(String taskType) {
        return """
                {
                  "code": 0,
                  "message": "success",
                  "requestId": "test-request",
                  "timestamp": "2026-07-12T00:00:00Z",
                  "data": {
                    "taskType": "%s",
                    "latencyMs": 1,
                    "detections": [],
                    "detectionCount": 0
                  }
                }
                """.formatted(taskType);
    }
}
