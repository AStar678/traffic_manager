package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.service.AlertService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/alerts")
@RequiredArgsConstructor
@Tag(name = "告警管理", description = "告警列表和统计")
public class AlertController {

    private final AlertService alertService;

    @Operation(summary = "获取告警列表")
    @GetMapping
    public ApiResponse<List<AlertEvent>> getAlertList(
            @Parameter(description = "告警级别: info/warning/critical")
            @RequestParam(required = false) String severity,

            @Parameter(description = "是否已处理")
            @RequestParam(required = false) Boolean resolved
    ) {
        List<AlertEvent> alerts = alertService.getAlertList(severity, resolved);
        return ApiResponse.success(alerts);
    }

    @Operation(summary = "获取告警统计")
    @GetMapping("/stats")
    public ApiResponse<Map<String, Object>> getAlertStats() {
        Map<String, Object> stats = alertService.getAlertStats();
        return ApiResponse.success(stats);
    }
}