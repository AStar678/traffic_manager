package com.visiondrive.agent;

public enum AlertSeverity {
    INFO("提示", "💡"),
    WARNING("警告", "⚠️"),
    CRITICAL("严重", "🔴");

    private final String label;
    private final String emoji;

    AlertSeverity(String label, String emoji) {
        this.label = label;
        this.emoji = emoji;
    }

    public String getLabel() {
        return label;
    }

    public String getEmoji() {
        return emoji;
    }
}