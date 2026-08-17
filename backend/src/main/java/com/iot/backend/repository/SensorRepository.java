package com.iot.backend.repository;

import com.iot.backend.entity.Sensor;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
@Repository
public interface SensorRepository extends JpaRepository<Sensor, Integer> {
}