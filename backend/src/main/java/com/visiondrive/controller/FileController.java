package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.service.FileStorageService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/files")
@RequiredArgsConstructor
@Tag(name = "文件服务", description = "图片/视频上传")
public class FileController {

    private final FileStorageService fileStorageService;

    @Operation(
            summary = "上传图片",
            description = "上传图片文件，返回可访问的URL"
    )
    @PostMapping(
            value = "/upload/image",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<Map<String, String>> uploadImage(
            @Parameter(description = "图片文件", required = true)
            @RequestParam("file") MultipartFile file
    ) {
        String url = fileStorageService.uploadFile(file, "images");
        Map<String, String> data = new HashMap<>();
        data.put("url", url);
        data.put("filename", file.getOriginalFilename());
        return ApiResponse.success(data);
    }

    @Operation(
            summary = "上传视频",
            description = "上传视频文件，返回可访问的URL"
    )
    @PostMapping(
            value = "/upload/video",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<Map<String, String>> uploadVideo(
            @Parameter(description = "视频文件", required = true)
            @RequestParam("file") MultipartFile file
    ) {
        String url = fileStorageService.uploadFile(file, "videos");
        Map<String, String> data = new HashMap<>();
        data.put("url", url);
        data.put("filename", file.getOriginalFilename());
        return ApiResponse.success(data);
    }
}