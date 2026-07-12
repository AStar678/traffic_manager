package com.visiondrive.common.exception;

import com.visiondrive.model.dto.ApiResponse;
import com.visiondrive.service.SystemLogService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
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
    public ResponseEntity<ApiResponse<Void>> handleBusinessException(BusinessException e) {
        log.error("业务异常: code={}, message={}", e.getCode(), e.getMessage());
        return ResponseEntity.status(resolveStatus(e.getCode()))
                .body(ApiResponse.error(e.getCode(), e.getMessage()));
    }

    /**
     * 处理文件过大异常
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiResponse<Void>> handleMaxUploadSizeException(MaxUploadSizeExceededException e) {
        log.error("文件过大: {}", e.getMessage());
        systemLogService.warn("user_operation", "upload_file_too_large", Map.of(
                "errorMessage", Objects.toString(e.getMessage(), "")
        ));
        return ResponseEntity.status(HttpStatus.PAYLOAD_TOO_LARGE)
                .body(ApiResponse.error(413, "文件大小超出限制，最大200MB"));
    }

    /**
     * 处理参数校验异常
     */
    @ExceptionHandler({IllegalArgumentException.class, HttpMessageNotReadableException.class})
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgumentException(Exception e) {
        log.error("参数错误: {}", e.getMessage());
        systemLogService.warn("user_operation", "bad_request", Map.of(
                "errorMessage", Objects.toString(e.getMessage(), "")
        ));
        return ResponseEntity.badRequest().body(ApiResponse.error(400, "请求参数格式不正确"));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidationException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(error -> error.getDefaultMessage())
                .orElse("请求参数校验失败");
        return ResponseEntity.badRequest().body(ApiResponse.error(400, message));
    }

    /**
     * 处理其他未捕获的异常
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleException(Exception e) {
        log.error("系统异常: ", e);
        systemLogService.error(resolveModule(e), resolveEvent(e), Map.of(
                "exception", e.getClass().getName(),
                "errorMessage", Objects.toString(e.getMessage(), "")
        ));
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(500, "系统内部错误，请稍后重试"));
    }

    private HttpStatus resolveStatus(Integer code) {
        HttpStatus status = code == null ? null : HttpStatus.resolve(code);
        return status == null ? HttpStatus.BAD_REQUEST : status;
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
