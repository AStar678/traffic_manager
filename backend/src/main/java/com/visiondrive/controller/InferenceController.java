package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.InferenceRequest;
import com.visiondrive.model.dto.InferenceResponse;
import com.visiondrive.service.InferenceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequestMapping("/api/v1/inference")
@RequiredArgsConstructor
@Tag(name = "推理接口", description = "调用算法服务进行车牌/交警手势/车主手势识别")
public class InferenceController {

    private final InferenceService inferenceService;

    @Operation(
            summary = "图片推理",
            description = "支持三种任务类型: license_plate / police_gesture / owner_gesture"
    )
    @PostMapping("/image")
    public ApiResponse<InferenceResponse> imageInference(
            @Valid @RequestBody InferenceRequest request
    ) {
        log.info("收到图片推理请求: taskType={}, imageUrl={}",
                request.getTaskType(), request.getImageUrl());

        InferenceResponse response = inferenceService.processImageInference(request);
        return ApiResponse.success(response);
    }
}