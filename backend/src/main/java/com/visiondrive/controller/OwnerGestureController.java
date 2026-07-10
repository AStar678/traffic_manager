package com.visiondrive.controller;

import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.service.OwnerGestureControlService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/owner-gestures")
@RequiredArgsConstructor
@Tag(name = "车主手势识别", description = "代理新的原型网络手势识别服务")
public class OwnerGestureController {

    private final AlgorithmClient algorithmClient;
    private final OwnerGestureControlService ownerGestureControlService;

    @GetMapping
    @Operation(summary = "查询手势库", description = "兼容入口，返回新原型库与识别配置")
    public ApiResponse<Map<String, Object>> listGestures() {
        return ApiResponse.success(algorithmClient.getOwnerGestureLibrary());
    }

    @PostMapping("/enroll")
    @Operation(summary = "直接录入手势", description = "使用前端采集的关键点特征向量写入新原型库")
    public ApiResponse<Map<String, Object>> enrollGesture(@RequestBody Map<String, Object> request) {
        log.info("收到新手势录入请求: gestureName={}", request.get("gestureName"));
        return ApiResponse.success(algorithmClient.enrollOwnerGesture(request));
    }

    @PutMapping("/{prototypeId}")
    @Operation(summary = "编辑原型手势", description = "修改新原型库中的手势名称、动作或参数")
    public ApiResponse<Map<String, Object>> updateGesture(
            @PathVariable String prototypeId,
            @RequestBody Map<String, Object> request
    ) {
        return ApiResponse.success(algorithmClient.updateOwnerGesture(prototypeId, request));
    }

    @DeleteMapping("/{prototypeId}")
    @Operation(summary = "删除原型手势", description = "删除新原型库中的单个手势")
    public ApiResponse<Map<String, Object>> deleteGesture(@PathVariable String prototypeId) {
        Map<String, Object> result = algorithmClient.deleteOwnerGesture(prototypeId);
        ownerGestureControlService.deleteBinding(prototypeId);
        return ApiResponse.success(result);
    }

    @GetMapping("/state")
    @Operation(summary = "查询识别状态", description = "返回原型库、录入状态、车辆状态和识别参数")
    public ApiResponse<Map<String, Object>> state() {
        return ApiResponse.success(algorithmClient.getOwnerGestureState());
    }

    @GetMapping("/config")
    @Operation(summary = "查询识别参数")
    public ApiResponse<Map<String, Object>> config() {
        return ApiResponse.success(algorithmClient.getOwnerGestureConfig());
    }

    @PatchMapping("/config")
    @Operation(summary = "局部更新识别参数")
    public ApiResponse<Map<String, Object>> patchConfig(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(algorithmClient.patchOwnerGestureConfig(request));
    }

    @PutMapping("/config")
    @Operation(summary = "完整替换识别参数")
    public ApiResponse<Map<String, Object>> putConfig(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(algorithmClient.putOwnerGestureConfig(request));
    }

    @GetMapping("/prototypes")
    @Operation(summary = "查询原型库")
    public ApiResponse<Map<String, Object>> prototypes() {
        return ApiResponse.success(algorithmClient.getOwnerGesturePrototypes());
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
    @Operation(summary = "单次识别", description = "输入关键点特征向量，返回原型匹配结果")
    public ApiResponse<Map<String, Object>> recognize(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(algorithmClient.recognizeOwnerGesture(request));
    }

    @GetMapping("/control-settings")
    @Operation(summary = "查询控制动作", description = "返回数据库中的手势与车辆功能绑定，未手动绑定的手势默认不触发控制")
    public ApiResponse<Map<String, Object>> getControlSettings() {
        return ApiResponse.success(ownerGestureControlService.getControlSettings());
    }

    @PostMapping("/control-settings")
    @Operation(summary = "保存控制动作", description = "将手势与车辆功能的绑定关系保存到数据库")
    public ApiResponse<Map<String, Object>> saveControlSettings(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(ownerGestureControlService.saveControlSettings(request));
    }

    @PostMapping("/control/execute")
    @Operation(summary = "执行手势控制", description = "根据识别出的手势查询数据库绑定，只有已启用绑定才返回车辆控制动作")
    public ApiResponse<Map<String, Object>> executeControl(@RequestBody Map<String, Object> request) {
        return ApiResponse.success(ownerGestureControlService.executeControl(request));
    }
}
