package com.iot.backend.controller;

import com.iot.backend.entity.DataSensor;
import com.iot.backend.entity.Sensor;
import com.iot.backend.repository.DataSensorRepository;
import com.iot.backend.repository.SensorRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;
import org.springframework.data.domain.Pageable;

import java.util.List;

@RestController
@RequestMapping("/api/sensors")
@CrossOrigin(origins = "*")
public class SensorController {

    @Autowired
    private SensorRepository sensorRepository;

    @Autowired
    private DataSensorRepository dataSensorRepository;

    // Lấy danh sách 3 loại cảm biến (Nhiệt độ, Độ ẩm, Ánh sáng)
    @GetMapping
    public List<Sensor> getAllSensors() {
        return sensorRepository.findAll();
    }

    // Tra cứu dữ liệu cảm biến phân trang + tìm kiếm theo sensorId (Trang Datasensor)
    @GetMapping("/data")
    public Page<DataSensor> getDataSensors(
            @RequestParam(required = false) Integer sensorId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        
        PageRequest pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "recordedAt"));
        
        if (sensorId != null) {
            return dataSensorRepository.findBySensorId(sensorId, pageable);
        }
        return dataSensorRepository.findAll(pageable);
    }
}