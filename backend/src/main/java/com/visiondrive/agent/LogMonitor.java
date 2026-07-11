package com.visiondrive.agent;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class LogMonitor {

    private final AlertAgent alertAgent;

    /**
     * 按配置周期执行异常检测
     */
    @Scheduled(fixedDelayString = "${alert.agent.poll-interval:30000}")
    public void monitor() {
        log.debug("开始执行异常检测...");

        try {
            List<AnomalyEvent> events = alertAgent.runOnce();

            if (events.isEmpty()) {
                log.debug("未检测到异常");
            } else {
                log.info("本轮告警智能体已处理 {} 个异常事件", events.size());
            }

        } catch (Exception e) {
            log.error("异常检测失败: {}", e.getMessage(), e);
        }
    }

    /**
     * 手动触发检测
     */
    public List<AnomalyEvent> manualDetect() {
        return alertAgent.runOnce(true);
    }
}
