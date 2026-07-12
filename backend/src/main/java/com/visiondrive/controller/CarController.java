package com.visiondrive.controller;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.model.dto.CarConfigurationRequest;
import com.visiondrive.model.dto.CarResponse;
import com.visiondrive.security.AuthenticatedUser;
import com.visiondrive.service.CarService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/cars")
@RequiredArgsConstructor
public class CarController {
    private final CarService carService;

    @GetMapping("/current")
    public ApiResponse<CarResponse> getCurrent(@AuthenticationPrincipal AuthenticatedUser principal) {
        return ApiResponse.success(carService.getCurrent(principal.id()));
    }

    @PutMapping("/current")
    public ApiResponse<CarResponse> updateCurrent(
            @AuthenticationPrincipal AuthenticatedUser principal,
            @Valid @RequestBody CarConfigurationRequest request
    ) {
        return ApiResponse.success(carService.updateCurrent(principal.id(), request));
    }
}
