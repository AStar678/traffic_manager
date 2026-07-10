package com.visiondrive.common.exception;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.service.SystemLogService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.util.Map;
import java.util.Objects;

@Slf4j
@RestControllerAdvice
@RequiredArgsConstructor
public class GlobalExceptionHandler {

    private final SystemLogService systemLogService;

    /**
     * 处理业务异常
     */
    @ExceptionHandler(BusinessException.class)
    public ApiResponse<Void> handleBusinessException(BusinessException e) {
        log.error("业务异常: code={}, message={}", e.getCode(), e.getMessage());
        return ApiResponse.error(e.getCode(), e.getMessage());
    }

    /**
     * 处理文件过大异常
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ApiResponse<Void> handleMaxUploadSizeException(MaxUploadSizeExceededException e) {
        log.error("文件过大: {}", e.getMessage());
        systemLogService.warn("user_operation", "upload_file_too_large", Map.of(
                "errorMessage", Objects.toString(e.getMessage(), "")
        ));
        return ApiResponse.error(400, "文件大小超出限制，最大200MB");
    }

    /**
     * 处理参数校验异常
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ApiResponse<Void> handleIllegalArgumentException(IllegalArgumentException e) {
        log.error("参数错误: {}", e.getMessage());
        systemLogService.warn("user_operation", "bad_request", Map.of(
                "errorMessage", Objects.toString(e.getMessage(), "")
        ));
        return ApiResponse.error(400, e.getMessage());
    }

    /**
     * 处理其他未捕获的异常
     */
    @ExceptionHandler(Exception.class)
    public ApiResponse<Void> handleException(Exception e) {
        log.error("系统异常: ", e);
        systemLogService.error(resolveModule(e), resolveEvent(e), Map.of(
                "exception", e.getClass().getName(),
                "errorMessage", Objects.toString(e.getMessage(), "")
        ));
        return ApiResponse.error(500, "系统内部错误，请稍后重试");
    }

    private String resolveModule(Exception e) {
        if (e instanceof DataAccessException) {
            return "database";
        }
        String message = Objects.toString(e.getMessage(), "").toLowerCase();
        if (message.contains("llm") || message.contains("deepseek") || message.contains("token")) {
            return "llm";
        }
        return "system";
    }

    private String resolveEvent(Exception e) {
        if (e instanceof DataAccessException) {
            return "connection_error";
        }
        String message = Objects.toString(e.getMessage(), "").toLowerCase();
        if (message.contains("timeout") || message.contains("timed out")) {
            return "timeout";
        }
        return "exception";
    }
}
