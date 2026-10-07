package com.iot.backend.repository;

import com.iot.backend.entity.DataSensor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface DataSensorRepository extends JpaRepository<DataSensor, Long> {
    
    // Tìm kiếm dữ liệu theo sensorId kèm phân trang
    Page<DataSensor> findBySensorId(Integer sensorId, Pageable pageable);

    @Query("SELECT d FROM DataSensor d WHERE " +
           "(:sensorId IS NULL OR d.sensor.id = :sensorId) AND " +
           "(:startTime IS NULL OR d.recordedAt >= :startTime) AND " +
           "(:endTime IS NULL OR d.recordedAt < :endTime)")
    Page<DataSensor> findByFilters(
            @Param("sensorId") Integer sensorId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            Pageable pageable);

    Optional<DataSensor> findTopBySensorIdOrderByRecordedAtDesc(Integer sensorId);
    
    // Lấy 3 dữ liệu gần nhất
    List<DataSensor> findTop3ByOrderByRecordedAtDesc();
    
    // Lọc theo loại cảm biến và khoảng thời gian
    @Query("SELECT d FROM DataSensor d WHERE d.sensor.type = :sensorType " +
           "AND d.recordedAt BETWEEN :startDate AND :endDate ORDER BY d.recordedAt DESC")
    Page<DataSensor> findBySensorTypeAndRecordedAtBetween(
            @Param("sensorType") String sensorType,
            @Param("startDate") LocalDateTime startDate,
            @Param("endDate") LocalDateTime endDate,
            Pageable pageable);
}
