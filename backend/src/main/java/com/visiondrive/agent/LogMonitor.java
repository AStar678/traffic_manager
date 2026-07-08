package com.visiondrive.agent;

import com.visiondrive.model.entity.SystemLog;
import com.visiondrive.repository.SystemLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class LogMonitor {

    private final SystemLogRepository systemLogRepository;
    private final AnomalyDetector anomalyDetector;
    private final AlertDispatcher alertDispatcher;

    /**
     * 每30秒执行一次异常检测
     */
    @Scheduled(fixedDelay = 30000)
    public void monitor() {
        log.debug("开始执行异常检测...");

        try {
            // 1. 检测所有异常
            List<AnomalyEvent> events = anomalyDetector.detectAll();

            // 2. 处理检测到的异常
            for (AnomalyEvent event : events) {
                log.info("检测到异常: {} - {}", event.getType().name(), event.getTitle());
                // 分发告警
                alertDispatcher.dispatch(event);
            }

            if (events.isEmpty()) {
                log.debug("未检测到异常");
            }

        } catch (Exception e) {
            log.error("异常检测失败: {}", e.getMessage(), e);
        }
    }

    /**
     * 手动触发检测
     */
    public List<AnomalyEvent> manualDetect() {
        List<AnomalyEvent> events = anomalyDetector.detectAll();
        for (AnomalyEvent event : events) {
            alertDispatcher.dispatch(event);
        }
        return events;
    }
}