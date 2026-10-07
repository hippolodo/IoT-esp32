package com.iot.backend.service;

import com.iot.backend.entity.DataSensor;
import com.iot.backend.repository.DataSensorRepository;
import com.iot.backend.repository.SensorRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;

/**
 * Sensor Service - Quản lý dữ liệu cảm biến
 */
@Slf4j
@Service
public class SensorService {

    @Autowired
    private DataSensorRepository dataSensorRepository;

    @Autowired
    private SensorRepository sensorRepository;

    /**
     * Lấy 3 giá trị đo gần nhất từ mỗi cảm biến (để hiển thị dashboard ban đầu)
     */
    public List<DataSensor> getLatestSensorData() {
        return sensorRepository.findAll().stream()
                .map(sensor -> dataSensorRepository.findTopBySensorIdOrderByRecordedAtDesc(sensor.getId()).orElse(null))
                .filter(Objects::nonNull)
                .sorted(Comparator.comparing(DataSensor::getRecordedAt).reversed())
                .toList();
    }

    /**
     * Lấy dữ liệu cảm biến có phân trang
     */
    public Page<DataSensor> getSensorDataPaginated(
            Integer sensorId, LocalDateTime startTime, LocalDateTime endTime, Pageable pageable) {
        return dataSensorRepository.findByFilters(sensorId, startTime, endTime, pageable);
    }

    /**
     * Lọc dữ liệu cảm biến theo kiểu và khoảng thời gian
     */
    public Page<DataSensor> filterSensorData(String sensorType, LocalDateTime startDate, LocalDateTime endDate, Pageable pageable) {
        return dataSensorRepository.findBySensorTypeAndRecordedAtBetween(sensorType, startDate, endDate, pageable);
    }
}
