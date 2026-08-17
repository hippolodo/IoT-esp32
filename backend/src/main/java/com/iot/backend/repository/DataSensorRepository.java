package com.iot.backend.repository;

import com.iot.backend.entity.DataSensor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface DataSensorRepository extends JpaRepository<DataSensor, Integer> {
    
    // Tìm kiếm dữ liệu theo sensorId kèm phân trang
    Page<DataSensor> findBySensorId(Integer sensorId, Pageable pageable);
}