package com.iot.backend.config;

import com.iot.backend.entity.Device;
import com.iot.backend.entity.Sensor;
import com.iot.backend.entity.User;
import com.iot.backend.repository.DeviceRepository;
import com.iot.backend.repository.SensorRepository;
import com.iot.backend.repository.UserRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Configuration;

import java.security.MessageDigest;
import java.time.LocalDateTime;

/**
 * DataInitializer - Khởi tạo dữ liệu mẫu khi ứng dụng lần đầu chạy
 * Tạo 3 thiết bị, 3 cảm biến, và 1 tài khoản admin
 */
@Slf4j
@Configuration
public class DataInitializer implements CommandLineRunner {

    @Autowired
    private DeviceRepository deviceRepo;

    @Autowired
    private SensorRepository sensorRepo;

    @Autowired
    private UserRepository userRepo;

    @Override
    public void run(String... args) throws Exception {
        log.info("========== Bắt đầu khởi tạo dữ liệu mẫu ==========");

        // 1. Khởi tạo thiết bị mẫu nếu bảng rỗng
        if (deviceRepo.count() == 0) {
            log.info("Tạo dữ liệu thiết bị mẫu...");
            
            Device d1 = new Device();
            d1.setName("Đèn phòng khách");
            d1.setPinGpio(18);
            d1.setStatus(0);
            d1.setUpdatedAt(LocalDateTime.now());
            deviceRepo.save(d1);

            Device d2 = new Device();
            d2.setName("Đèn phòng ngủ");
            d2.setPinGpio(19);
            d2.setStatus(0);
            d2.setUpdatedAt(LocalDateTime.now());
            deviceRepo.save(d2);

            Device d3 = new Device();
            d3.setName("Đèn ban công");
            d3.setPinGpio(21);
            d3.setStatus(0);
            d3.setUpdatedAt(LocalDateTime.now());
            deviceRepo.save(d3);
            
            log.info("✓ Tạo thành công 3 thiết bị");
        }

        // 2. Khởi tạo cảm biến mẫu nếu bảng rỗng
        if (sensorRepo.count() == 0) {
            log.info("Tạo dữ liệu cảm biến mẫu...");
            
            Sensor s1 = new Sensor();
            s1.setName("Cảm biến Nhiệt độ");
            s1.setType("TEMPERATURE");
            s1.setUnit("°C");
            s1.setPinGpio(4);
            s1.setMqttKey("temperature");
            s1.setModule("DHT11");
            sensorRepo.save(s1);

            Sensor s2 = new Sensor();
            s2.setName("Cảm biến Độ ẩm");
            s2.setType("HUMIDITY");
            s2.setUnit("%");
            s2.setPinGpio(4);
            s2.setMqttKey("humidity");
            s2.setModule("DHT11");
            sensorRepo.save(s2);

            Sensor s3 = new Sensor();
            s3.setName("Cảm biến Ánh sáng");
            s3.setType("LIGHT");
            s3.setUnit("lux");
            s3.setPinGpio(34);
            s3.setMqttKey("light");
            s3.setModule("LDR");
            sensorRepo.save(s3);
            
            log.info("✓ Tạo thành công 3 cảm biến");
        }

        synchronizeSensorMetadata("TEMPERATURE", "temperature", "DHT11");
        synchronizeSensorMetadata("HUMIDITY", "humidity", "DHT11");
        synchronizeSensorMetadata("LIGHT", "light", "LDR");

        // 3. Khởi tạo tài khoản Admin nếu bảng rỗng
        if (userRepo.count() == 0) {
            log.info("Tạo tài khoản Admin...");
            
            User user = new User();
            user.setUsername("admin");
            user.setPasswordHash(hashPassword("123456"));  // Password hash
            user.setFullName("Nguyễn Văn A");
            user.setEmail("admin@gmail.com");
            user.setCreatedAt(LocalDateTime.now());
            userRepo.save(user);
            
            log.info("✓ Tạo thành công tài khoản admin");
            log.info("   Username: admin");
            log.info("   Password: 123456");
        }
        
        log.info("========== Hoàn tất khởi tạo dữ liệu ==========");
    }

    /**
     * Mã hóa mật khẩu bằng SHA-256
     */
    private String hashPassword(String password) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encodedhash = digest.digest(password.getBytes());
            StringBuilder hexString = new StringBuilder();

            for (byte b : encodedhash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            throw new RuntimeException("Lỗi mã hóa mật khẩu", e);
        }
    }

    private void synchronizeSensorMetadata(String type, String mqttKey, String module) {
        sensorRepo.findByType(type).ifPresent(sensor -> {
            boolean changed = false;
            if (!mqttKey.equals(sensor.getMqttKey())) {
                sensor.setMqttKey(mqttKey);
                changed = true;
            }
            if (!module.equals(sensor.getModule())) {
                sensor.setModule(module);
                changed = true;
            }
            if (changed) {
                sensorRepo.save(sensor);
            }
        });
    }
}
