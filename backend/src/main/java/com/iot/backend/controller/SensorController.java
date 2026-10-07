package com.iot.backend.controller;

import com.iot.backend.dto.ApiResponse;
import com.iot.backend.dto.SensorDataResponse;
import com.iot.backend.entity.DataSensor;
import com.iot.backend.entity.Sensor;
import com.iot.backend.service.SensorService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.iot.backend.repository.SensorRepository;
import com.iot.backend.util.TimeRangeParser;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Sensor Controller - API lấy dữ liệu cảm biến
 * Endpoints: /api/sensors
 */
@Slf4j
@RestController
@RequestMapping("/api/sensors")
@CrossOrigin(origins = "*")
public class SensorController {

    @Autowired
    private SensorRepository sensorRepository;

    @Autowired
    private SensorService sensorService;

    private final DateTimeFormatter dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    /**
     * Lấy danh sách 3 loại cảm biến (Nhiệt độ, Độ ẩm, Ánh sáng)
     * GET /api/sensors
     */
    @GetMapping
    public ResponseEntity<ApiResponse<List<Sensor>>> getAllSensors() {
        try {
            List<Sensor> sensors = sensorRepository.findAll();
            return ResponseEntity.ok(ApiResponse.success(sensors, "Lấy danh sách cảm biến thành công"));
        } catch (Exception e) {
            log.error("Lỗi lấy danh sách cảm biến: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy danh sách cảm biến", 500));
        }
    }

    /**
     * Lấy 3 giá trị đo gần nhất của mỗi cảm biến (dashboard hiển thị nhanh)
     * GET /api/sensors/latest
     */
    @GetMapping("/latest")
    public ResponseEntity<ApiResponse<List<SensorDataResponse>>> getLatestSensorData() {
        try {
            List<DataSensor> data = sensorService.getLatestSensorData();
            List<SensorDataResponse> responses = data.stream()
                    .map(dataSensor -> SensorDataResponse.builder()
                            .id(dataSensor.getId())
                            .sensorId(dataSensor.getSensor().getId())
                            .sensorName(dataSensor.getSensor().getName())
                            .sensorType(dataSensor.getSensor().getType())
                            .unit(dataSensor.getSensor().getUnit())
                            .value(dataSensor.getValue())
                            .recordedAt(dataSensor.getRecordedAt() != null ?
                                    dataSensor.getRecordedAt().format(dateFormatter) : "N/A")
                            .build())
                    .collect(Collectors.toList());

            return ResponseEntity.ok(ApiResponse.success(responses, "Lấy dữ liệu cảm biến gần đây thành công"));
        } catch (Exception e) {
            log.error("Lỗi lấy dữ liệu cảm biến gần đây: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy dữ liệu cảm biến", 500));
        }
    }

    /**
     * Lấy danh sách dữ liệu cảm biến có phân trang
     * GET /api/sensors/data?sensorId=1&page=0&size=10
     * 
     * @param sensorId ID cảm biến (tùy chọn)
     * @param page Số trang (bắt đầu từ 0)
     * @param size Số bản ghi trên một trang
     */
    @GetMapping("/data")
    public ResponseEntity<ApiResponse<Page<SensorDataResponse>>> getDataSensors(
            @RequestParam(required = false) Integer sensorId,
            @RequestParam(required = false) String startTime,
            @RequestParam(required = false) String endTime,
            @RequestParam(defaultValue = "0") Integer page,
            @RequestParam(defaultValue = "10") Integer size) {
        try {
            if (page < 0 || size <= 0) {
                return ResponseEntity.status(400)
                        .body(ApiResponse.error("page phải lớn hơn hoặc bằng 0 và size phải lớn hơn 0", 400));
            }
            TimeRangeParser.TimeRange timeRange = TimeRangeParser.parse(startTime, endTime);
            Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "recordedAt"));
            Page<DataSensor> dataPage = sensorService.getSensorDataPaginated(
                    sensorId, timeRange.start(), timeRange.endExclusive(), pageable);

            Page<SensorDataResponse> responsePage = dataPage.map(dataSensor ->
                    SensorDataResponse.builder()
                            .id(dataSensor.getId())
                            .sensorId(dataSensor.getSensor().getId())
                            .sensorName(dataSensor.getSensor().getName())
                            .sensorType(dataSensor.getSensor().getType())
                            .unit(dataSensor.getSensor().getUnit())
                            .value(dataSensor.getValue())
                            .recordedAt(dataSensor.getRecordedAt() != null ?
                                    dataSensor.getRecordedAt().format(dateFormatter) : "N/A")
                            .build());

            return ResponseEntity.ok(ApiResponse.success(responsePage, "Lấy dữ liệu cảm biến thành công"));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(400)
                    .body(ApiResponse.error(e.getMessage(), 400));
        } catch (Exception e) {
            log.error("Lỗi lấy dữ liệu cảm biến: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy dữ liệu cảm biến", 500));
        }
    }

    /**
     * Lọc dữ liệu cảm biến theo loại và khoảng thời gian
     * GET /api/sensors/filter?type=Temperature&startDate=2024-01-01 00:00:00&endDate=2024-12-31 23:59:59&page=0&size=10
     * 
     * @param type Loại cảm biến (Temperature, Humidity, Light)
     * @param startDate Ngày bắt đầu
     * @param endDate Ngày kết thúc
     * @param page Số trang
     * @param size Số bản ghi trên một trang
     */
    @GetMapping("/filter")
    public ResponseEntity<ApiResponse<Page<SensorDataResponse>>> filterSensorData(
            @RequestParam String type,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endDate,
            @RequestParam(defaultValue = "0") Integer page,
            @RequestParam(defaultValue = "10") Integer size) {
        try {
            Pageable pageable = PageRequest.of(page, size);
            Page<DataSensor> dataPage = sensorService.filterSensorData(type, startDate, endDate, pageable);

            Page<SensorDataResponse> responsePage = dataPage.map(dataSensor ->
                    SensorDataResponse.builder()
                            .id(dataSensor.getId())
                            .sensorId(dataSensor.getSensor().getId())
                            .sensorName(dataSensor.getSensor().getName())
                            .sensorType(dataSensor.getSensor().getType())
                            .unit(dataSensor.getSensor().getUnit())
                            .value(dataSensor.getValue())
                            .recordedAt(dataSensor.getRecordedAt() != null ?
                                    dataSensor.getRecordedAt().format(dateFormatter) : "N/A")
                            .build());

            return ResponseEntity.ok(ApiResponse.success(responsePage, "Lọc dữ liệu cảm biến thành công"));
        } catch (Exception e) {
            log.error("Lỗi lọc dữ liệu cảm biến: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lọc dữ liệu cảm biến", 500));
        }
    }
}
