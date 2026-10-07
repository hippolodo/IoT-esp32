package com.iot.backend.config;

import com.iot.backend.service.MqttService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * ApplicationStartup - Khởi tạo MQTT Service khi ứng dụng khởi động
 */
@Slf4j
@Component
public class ApplicationStartup implements ApplicationRunner {

    @Autowired
    private MqttService mqttService;

    /**
     * Được gọi khi Spring Boot ApplicationContext khởi tạo xong
     */
    @Override
    public void run(ApplicationArguments args) throws Exception {
        try {
            log.info("========== Khởi động Backend IoT ==========");
            
            // Kết nối đến MQTT Broker
            mqttService.connect();
            
            log.info("========== Backend đã sẵn sàng ==========");
        } catch (Exception e) {
            log.error("Lỗi trong quá trình khởi startup: ", e);
        }
    }
}
