package com.iot.backend.config;

import com.iot.backend.entity.Device;
import com.iot.backend.entity.Sensor;
import com.iot.backend.entity.User;
import com.iot.backend.repository.DeviceRepository;
import com.iot.backend.repository.SensorRepository;
import com.iot.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final DeviceRepository deviceRepo;
    private final SensorRepository sensorRepo;
    private final UserRepository userRepo;

    @Override
    public void run(String... args) {
        if (deviceRepo.count() == 0) {
            Device d1 = new Device();
            d1.setName("Đèn phòng khách");
            d1.setPinGpio(18);
            d1.setStatus(0);

            Device d2 = new Device();
            d2.setName("Đèn phòng ngủ");
            d2.setPinGpio(19);
            d2.setStatus(0);

            Device d3 = new Device();
            d3.setName("Đèn ban công");
            d3.setPinGpio(21);
            d3.setStatus(0);

            deviceRepo.saveAll(List.of(d1, d2, d3));
        }

        if (sensorRepo.count() == 0) {
            Sensor s1 = new Sensor();
            s1.setName("Cảm biến Nhiệt độ");
            s1.setType("temperature");
            s1.setUnit("°C");
            s1.setPinGpio(4);

            Sensor s2 = new Sensor();
            s2.setName("Cảm biến Độ ẩm");
            s2.setType("humidity");
            s2.setUnit("%");
            s2.setPinGpio(4);

            Sensor s3 = new Sensor();
            s3.setName("Cảm biến Ánh sáng");
            s3.setType("light");
            s3.setUnit("lux");
            s3.setPinGpio(34);

            sensorRepo.saveAll(List.of(s1, s2, s3));
        }

        if (userRepo.count() == 0) {
            User user = new User();
            user.setUsername("admin");
            user.setPasswordHash("123456");
            user.setFullName("Nguyễn Văn A");
            user.setEmail("admin@gmail.com");

            userRepo.save(user);
        }
    }
}