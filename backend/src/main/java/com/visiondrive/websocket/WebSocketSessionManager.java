package com.visiondrive.websocket;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Component
public class WebSocketSessionManager {

    // 存储所有活跃的 WebSocket 会话
    private final CopyOnWriteArrayList<WebSocketSession> sessions = new CopyOnWriteArrayList<>();

    // 按用户ID存储会话（后续接入认证后使用）
    private final ConcurrentHashMap<Long, WebSocketSession> userSessions = new ConcurrentHashMap<>();

    public void addSession(WebSocketSession session) {
        sessions.add(session);
        System.out.println("WebSocket 连接已建立，当前连接数: " + sessions.size());
    }

    public void removeSession(WebSocketSession session) {
        sessions.remove(session);
        // 从用户映射中移除
        userSessions.values().remove(session);
        System.out.println("WebSocket 连接已断开，当前连接数: " + sessions.size());
    }

    public void bindUserToSession(Long userId, WebSocketSession session) {
        userSessions.put(userId, session);
    }

    public WebSocketSession getSessionByUserId(Long userId) {
        return userSessions.get(userId);
    }

    public CopyOnWriteArrayList<WebSocketSession> getAllSessions() {
        return sessions;
    }

    public int getActiveSessionCount() {
        return sessions.size();
    }
}