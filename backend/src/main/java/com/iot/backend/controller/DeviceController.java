package com.iot.backend.controller;

import com.iot.backend.dto.ApiResponse;
import com.iot.backend.dto.DeviceControlRequest;
import com.iot.backend.dto.DeviceResponse;
import com.iot.backend.entity.Device;
import com.iot.backend.service.DeviceService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Device Controller - API quản lý và điều khiển thiết bị
 * Endpoints: /api/devices
 */
@Slf4j
@RestController
@RequestMapping("/api/devices")
@CrossOrigin(origins = "*")
public class DeviceController {

    @Autowired
    private DeviceService deviceService;

    private final DateTimeFormatter dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    /**
     * Lấy danh sách tất cả thiết bị
     * GET /api/devices
     */
    @GetMapping
    public ResponseEntity<ApiResponse<List<DeviceResponse>>> getAllDevices() {
        try {
            List<Device> devices = deviceService.getAllDevices();
            List<DeviceResponse> responses = devices.stream()
                    .map(device -> DeviceResponse.builder()
                            .id(device.getId())
                            .name(device.getName())
                            .pinGpio(device.getPinGpio())
                            .status(device.getStatus())
                            .updatedAt(device.getUpdatedAt() != null ? 
                                    device.getUpdatedAt().format(dateFormatter) : "N/A")
                            .build())
                    .collect(Collectors.toList());

            return ResponseEntity.ok(ApiResponse.success(responses, "Lấy danh sách thiết bị thành công"));
        } catch (Exception e) {
            log.error("Lỗi lấy danh sách thiết bị: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy danh sách thiết bị", 500));
        }
    }

    /**
     * Lấy thông tin chi tiết một thiết bị
     * GET /api/devices/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<DeviceResponse>> getDeviceById(@PathVariable Integer id) {
        try {
            return deviceService.getDeviceById(id).map(device -> {
                DeviceResponse response = DeviceResponse.builder()
                        .id(device.getId())
                        .name(device.getName())
                        .pinGpio(device.getPinGpio())
                        .status(device.getStatus())
                        .updatedAt(device.getUpdatedAt() != null ? 
                                device.getUpdatedAt().format(dateFormatter) : "N/A")
                        .build();
                return ResponseEntity.ok(ApiResponse.success(response, "Lấy thông tin thiết bị thành công"));
            }).orElseGet(() -> ResponseEntity.status(404)
                    .body(ApiResponse.error("Không tìm thấy thiết bị", 404)));
        } catch (Exception e) {
            log.error("Lỗi lấy thông tin thiết bị: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy thông tin thiết bị", 500));
        }
    }

    /**
     * Điều khiển thiết bị (bằng request body)
     * POST /api/devices/control
     */
    @PostMapping("/control")
    public ResponseEntity<ApiResponse<String>> controlDevice(@RequestBody DeviceControlRequest request) {
        try {
            if (request.getStatus() != 0 && request.getStatus() != 1) {
                return ResponseEntity.status(400)
                        .body(ApiResponse.error("Status phải là 0 (OFF) hoặc 1 (ON)", 400));
            }

            deviceService.toggleDevice(request.getDeviceId(), request.getStatus());
            String message = request.getStatus() == 1 ? "Bật thiết bị thành công" : "Tắt thiết bị thành công";
            return ResponseEntity.ok(ApiResponse.success("OK", message));
        } catch (Exception e) {
            log.error("Lỗi điều khiển thiết bị: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi điều khiển thiết bị", 500));
        }
    }
}
