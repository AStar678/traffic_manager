package com.visiondrive.model.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.Instant;

/**
 * // 统一API响应
 * @param <T> 响应数据的类型
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "统一API响应")
public class ApiResponse<T> {   // ← 关键：加上 <T>

    @Schema(description = "状态码，0表示成功", example = "0")
    private Integer code;

    @Schema(description = "提示信息", example = "success")
    private String message;

    @Schema(description = "请求追踪ID", example = "req_1720320000000")
    private String requestId;

    @Schema(description = "时间戳", example = "2026-07-07T10:30:00+08:00")
    private String timestamp;

    @Schema(description = "业务数据")
    private T data;   // ← 关键：data 的类型是 T

    /**
     * 成功响应（带数据）
     */
    public static <T> ApiResponse<T> success(T data) {
        ApiResponse<T> response = new ApiResponse<>();
        response.setCode(0);
        response.setMessage("success");
        response.setRequestId(generateRequestId());
        response.setTimestamp(Instant.now().toString());
        response.setData(data);
        return response;
    }

    /**
     * 成功响应（无数据）
     */
    public static <T> ApiResponse<T> success() {
        return success(null);
    }

    /**
     * 失败响应
     */
    public static <T> ApiResponse<T> error(Integer code, String message) {
        ApiResponse<T> response = new ApiResponse<>();
        response.setCode(code);
        response.setMessage(message);
        response.setRequestId(generateRequestId());
        response.setTimestamp(Instant.now().toString());
        response.setData(null);
        return response;
    }

    /**
     * 失败响应（默认500）
     */
    public static <T> ApiResponse<T> error(String message) {
        return error(500, message);
    }

    /**
     * 生成请求ID
     */
    private static String generateRequestId() {
        return "req_" + System.currentTimeMillis();
    }
}