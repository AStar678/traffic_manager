package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.RecognitionRecordResponse;
import com.visiondrive.security.AuthenticatedUser;
import com.visiondrive.service.RecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@Slf4j
@RestController
@RequestMapping({ "/api/v1/records"})
@RequiredArgsConstructor
@Tag(name = "历史记录", description = "识别记录的查询和管理")
public class RecordController {

    private final RecordService recordService;

    @Operation(summary = "查询识别记录（分页）")
    @GetMapping
    public ApiResponse<Page<RecognitionRecordResponse>> queryRecords(
            @AuthenticationPrincipal AuthenticatedUser principal,

            @Parameter(description = "任务类型: license_plate/vehicle_type/police_gesture/owner_gesture")
            @RequestParam(required = false) String taskType,

            @Parameter(description = "识别结果或错误信息关键字")
            @RequestParam(required = false) String keyword,

            @Parameter(description = "是否成功")
            @RequestParam(required = false) Boolean success,

            @Parameter(description = "开始时间")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,

            @Parameter(description = "结束时间")
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime,

            @Parameter(description = "页码（从0开始）")
            @RequestParam(defaultValue = "0") int page,

            @Parameter(description = "每页数量")
            @RequestParam(defaultValue = "20") int size
    ) {
        Page<RecognitionRecordResponse> records = recordService.queryRecords(
                principal.id(), principal.role(), taskType, keyword, success, startTime, endTime, page, size
        );
        return ApiResponse.success(records);
    }

    @Operation(summary = "获取识别记录详情")
    @GetMapping("/{id}")
    public ApiResponse<RecognitionRecordResponse> getRecordDetail(
            @AuthenticationPrincipal AuthenticatedUser principal,
            @Parameter(description = "记录ID") @PathVariable Long id
    ) {
        RecognitionRecordResponse record = recordService.getRecordDetail(principal.id(), principal.role(), id);
        return ApiResponse.success(record);
    }
}
