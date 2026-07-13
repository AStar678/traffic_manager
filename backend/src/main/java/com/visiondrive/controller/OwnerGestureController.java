package com.visiondrive.controller;

import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.common.utils.JsonLogBuilder;
import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.security.AuthenticatedUser;
import com.visiondrive.service.OwnerGestureControlService;
import com.visiondrive.service.RecognitionHistoryService;
import com.visiondrive.service.SystemLogService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Slf4j
@RestController
@RequestMapping("/api/v1/owner-gestures")
@RequiredArgsConstructor
@Tag(name = "车主手势识别", description = "代理新的原型网络手势识别服务")
public class OwnerGestureController {

    private final AlgorithmClient algorithmClient;
    private final OwnerGestureControlService ownerGestureControlService;
    private final RecognitionHistoryService recognitionHistoryService;
    private final SystemLogService systemLogService;

    @GetMapping
    @Operation(summary = "查询手势库", description = "仅返回 DINOv2-TCN 用户录入的视频原型，不包含预设系统手势")
    public ApiResponse<Map<String, Object>> listGestures() {
        return ApiResponse.success(ownerGestureControlService.getPrototypeLibrary());
    }

    @PostMapping("/enroll")
    @Operation(summary = "直接录入手势", description = "DINOv2-TCN 手势应通过视频录入流程建立原型")
    public ApiResponse<Map<String, Object>> enrollGesture(@RequestBody Map<String, Object> request) {
        log.info("收到新手势录入请求: gestureName={}", request.get("gestureName"));
        Map<String, Object> result = algorithmClient.enrollOwnerGesture(request);
        systemLogService.info("user_operation", "owner_gesture_enroll", Map.of(
                "gestureName", Objects.toString(request.get("gestureName"), ""),
                "prototypeId", Objects.toString(result.get("prototypeId"), "")
        ));
        return ApiResponse.success(result);
    }

    @PutMapping("/{prototypeId}")
    @Operation(summary = "编辑原型手势", description = "修改新原型库中的手势名称、动作或参数")
    public ApiResponse<Map<String, Object>> updateGesture(
            @PathVariable String prototypeId,
            @RequestBody Map<String, Object> request
    ) {
        Map<String, Object> result = algorithmClient.updateOwnerGesture(prototypeId, request);
        systemLogService.info("user_operation", "owner_gesture_update", Map.of(
                "prototypeId", prototypeId,
                "gestureName", Objects.toString(request.get("gestureName"), "")
        ));
        return ApiResponse.success(result);
    }

    @DeleteMapping("/{prototypeId}")
    @Operation(summary = "删除原型手势", description = "删除新原型库中的单个手势")
    public ApiResponse<Map<String, Object>> deleteGesture(@PathVariable String prototypeId) {
        Map<String, Object> result = algorithmClient.deleteOwnerGesture(prototypeId);
        ownerGestureControlService.deleteBinding(prototypeId);
        systemLogService.warn("user_operation", "owner_gesture_delete", Map.of("prototypeId", prototypeId));
        return ApiResponse.success(result);
    }

    @GetMapping("/state")
    @Operation(summary = "查询识别状态", description = "仅返回 DINOv2-TCN 原型库、录入状态和相关参数")
    public ApiResponse<Map<String, Object>> state() {
        return ApiResponse.success(ownerGestureControlService.getRecognitionState());
    }

    @GetMapping("/config")
    @Operation(summary = "查询识别参数")
    public ApiResponse<Map<String, Object>> config() {
        return ApiResponse.success(ownerGestureControlService.getRecognitionConfig());
    }

    @PatchMapping("/config")
    @Operation(summary = "局部更新识别参数")
    public ApiResponse<Map<String, Object>> patchConfig(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(ownerGestureControlService.updateRecognitionConfig(request));
    }

    @PutMapping("/config")
    @Operation(summary = "更新 DINOv2-TCN 识别参数", description = "忽略旧 MediaPipe 原型网络参数")
    public ApiResponse<Map<String, Object>> putConfig(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(ownerGestureControlService.updateRecognitionConfig(request));
    }

    @GetMapping("/prototypes")
    @Operation(summary = "查询原型库")
    public ApiResponse<Map<String, Object>> prototypes() {
        return ApiResponse.success(ownerGestureControlService.getPrototypeLibrary());
    }

    @DeleteMapping("/prototypes")
    @Operation(summary = "清空原型库")
    public ApiResponse<Map<String, Object>> clearPrototypes() {
        return ApiResponse.success(algorithmClient.clearOwnerGesturePrototypes());
    }

    @DeleteMapping("/prototypes/{prototypeId}")
    @Operation(summary = "删除单个原型")
    public ApiResponse<Map<String, Object>> deletePrototype(@PathVariable String prototypeId) {
        Map<String, Object> result = algorithmClient.deleteOwnerGesturePrototype(prototypeId);
        ownerGestureControlService.deleteBinding(prototypeId);
        return ApiResponse.success(result);
    }

    @PostMapping("/recordings/start")
    @Operation(summary = "开始录入动作")
    public ApiResponse<Map<String, Object>> startRecording(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(algorithmClient.startOwnerGestureRecording(request));
    }

    @PostMapping("/recordings/cancel")
    @Operation(summary = "取消当前录入")
    public ApiResponse<Map<String, Object>> cancelRecording() {
        return ApiResponse.success(algorithmClient.cancelOwnerGestureRecording());
    }

    @PostMapping("/recognize")
    @Operation(summary = "单次识别", description = "输入 RGB 视频帧与手部几何特征，返回 DINOv2-TCN 原型匹配结果")
    public ApiResponse<Map<String, Object>> recognize(
            @AuthenticationPrincipal AuthenticatedUser principal,
            @RequestBody Map<String, Object> request
    ) {
        long started = System.currentTimeMillis();
        String traceId = JsonLogBuilder.generateTraceId();
        try {
            Map<String, Object> result = algorithmClient.recognizeOwnerGesture(request);
            Map<String, Object> detail = new LinkedHashMap<>();
            detail.put("gestureCode", firstString(result, "gestureCode", "gesture_code", "id"));
            detail.put("gestureName", firstString(result, "gestureName", "gesture_name", "label", "name"));
            detail.put("confidence", extractConfidence(result));
            detail.put("matched", result.getOrDefault("matched", result.getOrDefault("recognized", true)));
            recognitionHistoryService.saveOwnerGesture(
                    principal.id(), result, traceId, System.currentTimeMillis() - started, true, null
            );
            systemLogService.record(
                    "INFO", "owner_gesture", "success", JsonLogBuilder.toJson(detail), principal.id(), traceId
            );
            return ApiResponse.success(result);
        } catch (Exception e) {
            recognitionHistoryService.saveOwnerGesture(
                    principal.id(), null, traceId, System.currentTimeMillis() - started, false, e.getMessage()
            );
            systemLogService.record(
                    "ERROR",
                    "owner_gesture",
                    "failure",
                    JsonLogBuilder.toJson(Map.of("errorMessage", Objects.toString(e.getMessage(), ""))),
                    principal.id(),
                    traceId
            );
            throw e;
        }
    }

    @GetMapping("/control-settings")
    @Operation(summary = "查询控制动作", description = "返回数据库中的手势与车辆功能绑定，未手动绑定的手势默认不触发控制")
    public ApiResponse<Map<String, Object>> getControlSettings() {
        return ApiResponse.success(ownerGestureControlService.getControlSettings());
    }

    @PostMapping("/control-settings")
    @Operation(summary = "保存控制动作", description = "将手势与车辆功能的绑定关系保存到数据库")
    public ApiResponse<Map<String, Object>> saveControlSettings(@RequestBody Map<String, Object> request) {
        Map<String, Object> result = ownerGestureControlService.saveControlSettings(request);
        systemLogService.info("user_operation", "owner_gesture_control_settings_save", Map.of(
                "settingsCount", settingsCount(result.get("settings"))
        ));
        return ApiResponse.success(result);
    }

    @PostMapping("/control/execute")
    @Operation(summary = "执行手势控制", description = "根据识别出的手势查询数据库绑定，只有已启用绑定才返回车辆控制动作")
    public ApiResponse<Map<String, Object>> executeControl(@RequestBody Map<String, Object> request) {
        Map<String, Object> result = ownerGestureControlService.executeControl(request);
        systemLogService.info("user_operation", "owner_gesture_control_execute", Map.of(
                "gestureCode", Objects.toString(result.get("gestureCode"), ""),
                "gestureName", Objects.toString(result.get("gestureName"), ""),
                "actionType", Objects.toString(result.get("actionType"), ""),
                "enabled", result.getOrDefault("enabled", false)
        ));
        return ApiResponse.success(result);
    }

    private String firstString(Map<String, Object> result, String... keys) {
        for (String key : keys) {
            Object value = result.get(key);
            if (value != null && !Objects.toString(value, "").isBlank()) {
                return Objects.toString(value);
            }
        }
        return "";
    }

    private Double extractConfidence(Map<String, Object> result) {
        for (String key : List.of("confidence", "score", "similarity", "avgConfidence")) {
            Object value = result.get(key);
            Double parsed = toDouble(value);
            if (parsed != null) {
                return parsed;
            }
        }
        Object recognition = result.get("recognition");
        if (recognition instanceof Map<?, ?> recognitionMap) {
            for (String key : List.of("confidence", "score", "similarity")) {
                Double parsed = toDouble(recognitionMap.get(key));
                if (parsed != null) {
                    return parsed;
                }
            }
        }
        return null;
    }

    private Double toDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value != null) {
            try {
                return Double.parseDouble(Objects.toString(value));
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private int settingsCount(Object settings) {
        return settings instanceof List<?> list ? list.size() : 0;
    }
}
