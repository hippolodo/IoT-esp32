package com.iot.backend.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * Cấu hình WebSocket STOMP cho giao tiếp real-time giữa Backend và Frontend
 * - Endpoint: /ws (kết nối WebSocket)
 * - Tiền tố tin nhắn: /topic (broadcast), /queue (point-to-point)
 * - Application destination: /app (xử lý tin nhắn từ client)
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    /**
     * Cấu hình message broker cho việc gửi tin nhắn real-time
     */
    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Cấu hình in-memory message broker với tiền tố /topic (broadcast) và /queue (point-to-point)
        config.enableSimpleBroker("/topic", "/queue")
                .setHeartbeatValue(new long[]{0, 0});  // Heartbeat để giữ kết nối sống

        // Đặt tiền tố cho các tin nhắn từ client gửi tới server
        config.setApplicationDestinationPrefixes("/app");
    }

    /**
     * Đăng ký endpoint WebSocket cho client kết nối
     */
    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // Đăng ký endpoint /ws với SockJS fallback (cho các browser cũ không hỗ trợ WebSocket)
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("http://localhost:*", "http://127.0.0.1:*")
                .withSockJS()
                .setHeartbeatTime(30000)  // Heartbeat mỗi 30 giây
                .setSessionCookieNeeded(true);
    }
}
