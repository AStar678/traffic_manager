package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.service.StreamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/cameras")
@RequiredArgsConstructor
@Tag(name = "摄像头推流", description = "沙盘摄像头实时推流管理")
public class StreamController {

    private final StreamService streamService;

    @Operation(summary = "启动摄像头推流")
    @PostMapping("/{cameraId}/stream/start")
    public ApiResponse<Map<String, Object>> startStream(@PathVariable String cameraId) {
        Map<String, Object> result = streamService.startStream(cameraId);
        if (Boolean.TRUE.equals(result.get("success"))) {
            return ApiResponse.success(result);
        }
        return ApiResponse.error(500, (String) result.get("message"));
    }

    @Operation(summary = "停止摄像头推流")
    @PostMapping("/{cameraId}/stream/stop")
    public ApiResponse<Map<String, Object>> stopStream(@PathVariable String cameraId) {
        return ApiResponse.success(streamService.stopStream(cameraId));
    }

    @Operation(summary = "查询运行中的推流")
    @GetMapping("/streams")
    public ApiResponse<Map<String, Object>> getRunningStreams() {
        return ApiResponse.success(streamService.getRunningStreams());
    }
}
