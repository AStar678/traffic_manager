package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.CameraSlotRequest;
import com.visiondrive.model.dto.CameraSlotResponse;
import com.visiondrive.model.dto.CameraWeatherSimulationRequest;
import com.visiondrive.service.CameraManagerService;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/cameras")
@RequiredArgsConstructor
@Tag(name = "摄像头管理", description = "主服务内置的三路摄像头管理与文件帧输出")
public class CameraController {

    private final CameraManagerService cameraManagerService;

    @GetMapping("/slots")
    public ApiResponse<Map<String, Object>> listSlots() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("slots", cameraManagerService.listSlots());
        data.put("sourceTypes", cameraManagerService.sourceTypes());
        data.put("sandboxPresets", cameraManagerService.sandboxPresets());
        return ApiResponse.success(data);
    }

    @PutMapping("/slots/{slotId}")
    public ApiResponse<CameraSlotResponse> updateSlot(
            @PathVariable int slotId,
            @Valid @RequestBody CameraSlotRequest request
    ) {
        return ApiResponse.success(cameraManagerService.updateSlot(slotId, request));
    }

    @PatchMapping("/slots/{slotId}/weather-simulation")
    public ApiResponse<CameraSlotResponse> updateWeatherSimulation(
            @PathVariable int slotId,
            @Valid @RequestBody CameraWeatherSimulationRequest request
    ) {
        return ApiResponse.success(cameraManagerService.updateWeatherSimulation(slotId, request.getEnabled()));
    }

    @PostMapping(value = "/slots/{slotId}/media", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<CameraSlotResponse> uploadMedia(
            @PathVariable int slotId,
            @RequestParam("file") MultipartFile file
    ) {
        return ApiResponse.success(cameraManagerService.uploadMedia(slotId, file));
    }

    @GetMapping(value = "/slots/{slotId}/frame.jpg", produces = MediaType.IMAGE_JPEG_VALUE)
    public ResponseEntity<FileSystemResource> frame(@PathVariable int slotId) {
        Path frame = cameraManagerService.currentFramePath(slotId);
        return ResponseEntity.ok()
                .cacheControl(CacheControl.noStore())
                .contentType(MediaType.IMAGE_JPEG)
                .body(new FileSystemResource(frame));
    }
}
