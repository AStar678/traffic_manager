package com.visiondrive.agent;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 告警智能体核心：感知系统日志，决策告警级别，并执行持久化与通知。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AlertAgent {

    private final AnomalyDetector anomalyDetector;
    private final AlertDispatcher alertDispatcher;
    private final Map<AnomalyType, Long> lastDispatchedAt = new ConcurrentHashMap<>();

    @Value("${alert.agent.enabled:true}")
    private boolean enabled;

    @Value("${alert.agent.cooldown:300000}")
    private long cooldownMs;

    public List<AnomalyEvent> runOnce() {
        return runOnce(false);
    }

    public List<AnomalyEvent> runOnce(boolean ignoreCooldown) {
        if (!enabled) {
            log.debug("告警智能体已关闭，跳过本轮检测");
            return List.of();
        }

        List<AnomalyEvent> perceivedEvents = anomalyDetector.detectAll();
        List<AnomalyEvent> dispatchedEvents = new ArrayList<>();

        for (AnomalyEvent event : perceivedEvents) {
            if (!ignoreCooldown && isInCooldown(event)) {
                log.debug("告警仍在冷却期内，跳过重复发送: {}", event.getType());
                continue;
            }
            alertDispatcher.dispatch(event);
            lastDispatchedAt.put(event.getType(), System.currentTimeMillis());
            dispatchedEvents.add(event);
        }

        return dispatchedEvents;
    }

    private boolean isInCooldown(AnomalyEvent event) {
        Long lastAt = lastDispatchedAt.get(event.getType());
        return lastAt != null && System.currentTimeMillis() - lastAt < cooldownMs;
    }
}
