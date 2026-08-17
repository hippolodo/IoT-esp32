package com.iot.backend.controller;

import com.iot.backend.entity.Device;
import com.iot.backend.entity.History;
import com.iot.backend.repository.DeviceRepository;
import com.iot.backend.repository.HistoryRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/devices")
@CrossOrigin(origins = "*")
public class DeviceController {

    @Autowired
    private DeviceRepository deviceRepository;

    @Autowired
    private HistoryRepository historyRepository;

    // 1. Lấy danh sách toàn bộ thiết bị (3 đèn)
    @GetMapping
    public List<Device> getAllDevices() {
        return deviceRepository.findAll();
    }

    // 2. API bật/tắt thiết bị
    @PostMapping("/{id}/toggle")
    public ResponseEntity<?> toggleDevice(@PathVariable Integer id, @RequestParam Integer status) {
        return deviceRepository.findById(id).map(device -> {
            device.setStatus(status);
            deviceRepository.save(device);

            // Lưu lịch sử bật/tắt
            History history = new History();
            history.setDevice(device);
            history.setAction(status == 1 ? "ON" : "OFF");
            history.setStatus("SUCCESS");
            historyRepository.save(history);

            return ResponseEntity.ok(device);
        }).orElse(ResponseEntity.notFound().build());
    }
}