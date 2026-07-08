package com.visiondrive.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.HashMap;
import java.util.Map;

@Component
public class AlertWebSocketHandler extends TextWebSocketHandler {

    private final WebSocketSessionManager sessionManager;
    private final ObjectMapper objectMapper;

    public AlertWebSocketHandler(WebSocketSessionManager sessionManager) {
        this.sessionManager = sessionManager;
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        sessionManager.addSession(session);
        System.out.println("WebSocket 连接建立: " + session.getId());

        // 发送连接成功消息
        Map<String, Object> response = new HashMap<>();
        response.put("type", "connection");
        response.put("message", "连接成功");
        response.put("sessionId", session.getId());
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(response)));
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("收到客户端消息: " + payload);

        // 简单回显（后续可扩展为处理客户端请求）
        Map<String, Object> response = new HashMap<>();
        response.put("type", "echo");
        response.put("message", "收到消息: " + payload);
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(response)));
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        sessionManager.removeSession(session);
        System.out.println("WebSocket 连接关闭: " + session.getId() + ", 原因: " + status);
    }

    /**
     * 推送告警消息给所有连接的客户端
     */
    public void pushAlertToAllClients(Map<String, Object> alertData) {
        try {
            String alertJson = objectMapper.writeValueAsString(alertData);
            TextMessage textMessage = new TextMessage(alertJson);

            for (WebSocketSession session : sessionManager.getAllSessions()) {
                if (session.isOpen()) {
                    session.sendMessage(textMessage);
                }
            }
            System.out.println("告警已推送给所有客户端: " + alertData.get("title"));
        } catch (Exception e) {
            System.err.println("推送告警失败: " + e.getMessage());
        }
    }

    /**
     * 推送告警给特定用户
     */
    public void pushAlertToUser(Long userId, Map<String, Object> alertData) {
        try {
            WebSocketSession session = sessionManager.getSessionByUserId(userId);
            if (session != null && session.isOpen()) {
                String alertJson = objectMapper.writeValueAsString(alertData);
                session.sendMessage(new TextMessage(alertJson));
                System.out.println("告警已推送给用户 " + userId);
            }
        } catch (Exception e) {
            System.err.println("推送告警给用户失败: " + e.getMessage());
        }
    }
}