package com.iot.backend.service;

import com.iot.backend.entity.Device;
import com.iot.backend.entity.History;
import com.iot.backend.repository.DeviceRepository;
import com.iot.backend.repository.HistoryRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Device Service - Quản lý thiết bị và điều khiển
 */
@Slf4j
@Service
public class DeviceService {

    @Autowired
    private DeviceRepository deviceRepository;

    @Autowired
    private HistoryRepository historyRepository;

    @Autowired
    private MqttService mqttService;

    /**
     * Lấy tất cả thiết bị
     */
    public List<Device> getAllDevices() {
        return deviceRepository.findAll();
    }

    /**
     * Lấy thông tin chi tiết một thiết bị
     */
    public Optional<Device> getDeviceById(Integer id) {
        return deviceRepository.findById(id);
    }

    /**
     * Điều khiển thiết bị (bật/tắt)
     * @param deviceId ID của thiết bị
     * @param status Trạng thái mới (1 = ON, 0 = OFF)
     */
    public void toggleDevice(Integer deviceId, Integer status) {
        Device device = deviceRepository.findById(deviceId).orElse(null);
        if (device != null) {
            device.setStatus(status);
            device.setUpdatedAt(LocalDateTime.now());
            deviceRepository.save(device);

            // Lưu lịch sử hành động
            History history = new History();
            history.setDevice(device);
            history.setAction(status == 1 ? "ON" : "OFF");
            history.setStatus("PENDING");  // Chờ phản hồi từ ESP32
            history.setTimestamp(LocalDateTime.now());
            historyRepository.save(history);

            // Gửi lệnh qua MQTT tới ESP32
            String action = status == 1 ? "ON" : "OFF";
            mqttService.sendDeviceControl(deviceId, device.getPinGpio(), action);

            log.info("Gửi lệnh điều khiển thiết bị " + deviceId + " với trạng thái: " + action);
        }
    }

    /**
     * Lấy lịch sử hành động có phân trang
     */
    public Page<History> getHistoryPaginated(
            Integer deviceId, String status, LocalDateTime startTime, LocalDateTime endTime, Pageable pageable) {
        return historyRepository.findByFilters(deviceId, status, startTime, endTime, pageable);
    }

    /**
     * Lọc lịch sử theo deviceId, status và khoảng thời gian
     */
    public Page<History> filterHistory(Integer deviceId, String status, LocalDateTime startTime, LocalDateTime endTime, Pageable pageable) {
        return historyRepository.findByDeviceIdAndStatusAndTimestampBetween(deviceId, status, startTime, endTime, pageable);
    }
}
