package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.JobRequest;
import com.visiondrive.model.dto.JobStatusResponse;
import com.visiondrive.service.JobService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/v1/jobs")
@RequiredArgsConstructor
@Tag(name = "视频异步任务", description = "创建/查询/取消视频识别任务")
public class JobController {

    private final JobService jobService;

    @Operation(summary = "创建视频识别任务")
    @PostMapping
    public ApiResponse<JobStatusResponse> createJob(@RequestBody JobRequest request) {
        JobStatusResponse response = jobService.createJob(request);
        return ApiResponse.success(response);
    }

    @Operation(summary = "查询任务状态")
    @GetMapping("/{jobId}")
    public ApiResponse<JobStatusResponse> getJobStatus(@PathVariable String jobId) {
        JobStatusResponse response = jobService.getJobStatus(jobId);
        return ApiResponse.success(response);
    }

    @Operation(summary = "取消任务")
    @PostMapping("/{jobId}/cancel")
    public ApiResponse<JobStatusResponse> cancelJob(@PathVariable String jobId) {
        JobStatusResponse response = jobService.cancelJob(jobId);
        return ApiResponse.success(response);
    }
}