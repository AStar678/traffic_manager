package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.InferenceRequest;
import com.visiondrive.model.dto.InferenceResponse;
import com.visiondrive.model.dto.CameraInferenceRequest;
import com.visiondrive.model.dto.MultiCameraInferenceResponse;
import com.visiondrive.security.AuthenticatedUser;
import com.visiondrive.service.InferenceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequestMapping("/api/v1/inference")
@RequiredArgsConstructor
@Tag(name = "推理接口", description = "按任务类型路由到独立车牌、车辆类型或交警手势算法服务")
public class InferenceController {

    private final InferenceService inferenceService;

    @Operation(
            summary = "图片推理",
            description = "支持 license_plate、vehicle_type 与 police_gesture；车主手势使用 /api/v1/owner-gestures"
    )
    @PostMapping("/image")
    public ApiResponse<InferenceResponse> imageInference(
            @AuthenticationPrincipal AuthenticatedUser principal,
            @Valid @RequestBody InferenceRequest request
    ) {
        log.info("收到图片推理请求: taskType={}, imageUrl={}",
                request.getTaskType(), request.getImageUrl());

        InferenceResponse response = inferenceService.processImageInference(request, principal.id());
        return ApiResponse.success(response);
    }

    @Operation(
            summary = "三路摄像头并发推理",
            description = "主服务并发采集三路摄像头文件帧，并将本地文件路径传给车牌、车辆类型或交警算法"
    )
    @PostMapping("/cameras")
    public ApiResponse<MultiCameraInferenceResponse> cameraInference(
            @AuthenticationPrincipal AuthenticatedUser principal,
            @Valid @RequestBody CameraInferenceRequest request
    ) {
        return ApiResponse.success(inferenceService.processCameraInference(
                request.getTaskType(),
                Boolean.TRUE.equals(request.getIncludeVisuals()),
                principal.id()
        ));
    }
}
