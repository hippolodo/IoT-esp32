package com.iot.backend.config;

import com.iot.backend.entity.Device;
import com.iot.backend.entity.Sensor;
import com.iot.backend.entity.User;
import com.iot.backend.repository.DeviceRepository;
import com.iot.backend.repository.SensorRepository;
import com.iot.backend.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Configuration;

import java.time.LocalDateTime;

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
        // 1. Khởi tạo thiết bị mẫu nếu bảng rỗng
        if (deviceRepo.count() == 0) {
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
        }

        // 2. Khởi tạo cảm biến mẫu nếu bảng rỗng
        if (sensorRepo.count() == 0) {
            Sensor s1 = new Sensor();
            s1.setName("Cảm biến Nhiệt độ");
            s1.setType("TEMPERATURE");
            s1.setUnit("°C");
            s1.setPinGpio(4);
            sensorRepo.save(s1);

            Sensor s2 = new Sensor();
            s2.setName("Cảm biến Độ ẩm");
            s2.setType("HUMIDITY");
            s2.setUnit("%");
            s2.setPinGpio(4);
            sensorRepo.save(s2);

            Sensor s3 = new Sensor();
            s3.setName("Cảm biến Ánh sáng");
            s3.setType("LIGHT");
            s3.setUnit("lux");
            s3.setPinGpio(34);
            sensorRepo.save(s3);
        }

        // 3. Khởi tạo tài khoản Admin nếu bảng rỗng
        if (userRepo.count() == 0) {
            User user = new User();
            user.setUsername("admin");
            user.setPasswordHash("123456");
            user.setFullName("Nguyễn Văn A");
            user.setEmail("admin@gmail.com");
            user.setCreatedAt(LocalDateTime.now());
            userRepo.save(user);
        }
    }
}