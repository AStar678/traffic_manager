package com.visiondrive.controller;

import com.visiondrive.agent.AnomalyEvent;
import com.visiondrive.agent.LogMonitor;
import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.entity.AlertEvent;
import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.service.AlertService;
import com.visiondrive.service.EvidenceProxyService;
import com.visiondrive.service.ManualAlertInjectionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping({"/api/v1/alerts"})
@RequiredArgsConstructor
@Tag(name = "告警管理", description = "告警列表和统计")
public class AlertController {

    private final AlertService alertService;
    private final LogMonitor logMonitor;
    private final EvidenceProxyService evidenceProxyService;
    private final ManualAlertInjectionService manualAlertInjectionService;

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

    @Operation(summary = "读取失败样本图片或视频")
    @GetMapping("/evidence")
    public ResponseEntity<byte[]> getEvidence(@RequestParam String source) {
        return evidenceProxyService.load(source);
    }

    @Operation(summary = "获取告警详情")
    @GetMapping("/{id}")
    public ApiResponse<AlertEvent> getAlertDetail(@PathVariable Long id) {
        return ApiResponse.success(alertService.getAlertDetail(id));
    }

    @Operation(summary = "更新告警处理状态")
    @PutMapping("/{id}/status")
    public ApiResponse<AlertEvent> updateAlertStatus(
            @PathVariable Long id,
            @RequestBody Map<String, String> body
    ) {
        return ApiResponse.success(alertService.updateAlertStatus(id, body.get("status")));
    }

    @Operation(summary = "查询系统监控日志")
    @GetMapping("/system-logs")
    public ApiResponse<List<SystemLog>> getSystemLogs(
            @Parameter(description = "模块: license_plate/owner_gesture/police_gesture/auth/llm/database/system")
            @RequestParam(required = false) String module,

            @Parameter(description = "事件: success/failure/timeout/unauthorized/connection_error")
            @RequestParam(required = false) String event,

            @Parameter(description = "日志级别: INFO/WARN/ERROR")
            @RequestParam(required = false) String level,

            @Parameter(description = "返回条数，默认100，最大500")
            @RequestParam(required = false) Integer limit
    ) {
        return ApiResponse.success(alertService.getSystemLogs(module, event, level, limit));
    }

    @Operation(summary = "手动触发告警智能体检测")
    @PostMapping("/agent/run")
    public ApiResponse<List<AnomalyEvent>> runAlertAgent() {
        return ApiResponse.success(logMonitor.manualDetect());
    }

    @Operation(summary = "手动注入数据库连接失败严重告警")
    @PostMapping("/manual/database-failure")
    public ApiResponse<Map<String, Object>> injectDatabaseFailureAlert() {
        return ApiResponse.success(manualAlertInjectionService.injectDatabaseConnectionFailure());
    }
}
