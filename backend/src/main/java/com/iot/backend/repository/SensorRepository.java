package com.iot.backend.repository;

import com.iot.backend.entity.Sensor;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface SensorRepository extends JpaRepository<Sensor, Integer> {
    
    // Tìm cảm biến theo tên
    Optional<Sensor> findByName(String name);

    Optional<Sensor> findByMqttKey(String mqttKey);
    
    // Tìm cảm biến theo loại
    Optional<Sensor> findByType(String type);
}
