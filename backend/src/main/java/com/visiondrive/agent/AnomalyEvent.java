package com.visiondrive.agent;

import lombok.Data;

@Data
public class AnomalyEvent {
    private AnomalyType type;
    private AlertSeverity severity;
    private String title;
    private String summary;
    private String metrics;
    private String suggestedActions;
    private String affectedModule;
    private long timestamp;

    public AnomalyEvent() {
        this.timestamp = System.currentTimeMillis();
    }

    public String getAffectedModule() {
        return type != null ? type.getModule() : "unknown";
    }
}