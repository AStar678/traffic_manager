package com.visiondrive.config;

import com.visiondrive.client.AlgorithmClient;
import com.visiondrive.service.OwnerGestureControlService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.util.Map;

import static com.visiondrive.client.AlgorithmClient.OWNER_GESTURE_ALGORITHM;

@Slf4j
@Component
@RequiredArgsConstructor
public class OwnerGestureAlgorithmInitializer {

    private final AlgorithmClient algorithmClient;
    private final OwnerGestureControlService ownerGestureControlService;

    @EventListener(ApplicationReadyEvent.class)
    public void initialize() {
        try {
            Map<String, Object> state = algorithmClient.activateOwnerGestureAlgorithm();
            if (!isDinov2Active(state)) {
                throw new IllegalStateException("算法服务未确认启用 " + OWNER_GESTURE_ALGORITHM);
            }
            int removed = ownerGestureControlService.reconcileBindings();
            log.info("车主手势已固定为 DINOv2-TCN 视频原型算法，清理无效旧绑定 {} 条", removed);
        } catch (RuntimeException exception) {
            // 算法服务短暂离线不应阻止后端其余模块启动；手势接口会继续返回明确的调用失败。
            log.error("初始化 DINOv2-TCN 车主手势算法失败，已跳过数据库清理: {}", exception.getMessage());
        }
    }

    private boolean isDinov2Active(Map<String, Object> state) {
        Object algorithm = state.get("algorithm");
        if (!(algorithm instanceof Map<?, ?> values)) {
            return false;
        }
        return OWNER_GESTURE_ALGORITHM.equals(String.valueOf(values.get("active")));
    }
}
