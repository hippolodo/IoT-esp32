package com.iot.backend.controller;

import com.iot.backend.dto.ApiResponse;
import com.iot.backend.dto.HistoryResponse;
import com.iot.backend.entity.History;
import com.iot.backend.service.DeviceService;
import com.iot.backend.util.TimeRangeParser;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * History Controller - API lấy lịch sử hành động thiết bị
 * Endpoints: /api/history
 */
@Slf4j
@RestController
@RequestMapping("/api/history")
@CrossOrigin(origins = "*")
public class HistoryController {

    @Autowired
    private DeviceService deviceService;

    private final DateTimeFormatter dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    /**
     * Lấy lịch sử bật/tắt thiết bị có phân trang
     * GET /api/history?page=0&size=10
     * 
     * @param page Số trang (bắt đầu từ 0)
     * @param size Số bản ghi trên một trang
     */
    @GetMapping
    public ResponseEntity<ApiResponse<Page<HistoryResponse>>> getHistory(
            @RequestParam(required = false) Integer deviceId,
            @RequestParam(required = false) String status,
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
            Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
            Page<History> historyPage = deviceService.getHistoryPaginated(
                    deviceId, status, timeRange.start(), timeRange.endExclusive(), pageable);

            Page<HistoryResponse> responsePage = historyPage.map(history ->
                    HistoryResponse.builder()
                            .id(history.getId().intValue())
                            .deviceId(history.getDevice().getId())
                            .deviceName(history.getDevice().getName())
                            .action(history.getAction())
                            .status(history.getStatus())
                            .timestamp(history.getTimestamp() != null ?
                                    history.getTimestamp().format(dateFormatter) : "N/A")
                            .build());

            return ResponseEntity.ok(ApiResponse.success(responsePage, "Lấy lịch sử thành công"));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(400)
                    .body(ApiResponse.error(e.getMessage(), 400));
        } catch (Exception e) {
            log.error("Lỗi lấy lịch sử: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lấy lịch sử", 500));
        }
    }

    /**
     * Lọc lịch sử theo deviceId, status và khoảng thời gian
     * GET /api/history/filter?deviceId=1&status=SUCCESS&startTime=2024-01-01 00:00:00&endTime=2024-12-31 23:59:59&page=0&size=10
     * 
     * @param deviceId ID của thiết bị
     * @param status Trạng thái: SUCCESS, FAILED, PENDING
     * @param startTime Thời gian bắt đầu
     * @param endTime Thời gian kết thúc
     * @param page Số trang
     * @param size Số bản ghi trên một trang
     */
    @GetMapping("/filter")
    public ResponseEntity<ApiResponse<Page<HistoryResponse>>> filterHistory(
            @RequestParam(required = false) Integer deviceId,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime,
            @RequestParam(defaultValue = "0") Integer page,
            @RequestParam(defaultValue = "10") Integer size) {
        try {
            // Nếu không có startTime/endTime, sử dụng toàn bộ khoảng thời gian
            if (startTime == null) {
                startTime = LocalDateTime.of(2000, 1, 1, 0, 0, 0);
            }
            if (endTime == null) {
                endTime = LocalDateTime.now();
            }

            if (deviceId == null || status == null) {
                return ResponseEntity.status(400)
                        .body(ApiResponse.error("deviceId và status không được để trống", 400));
            }

            Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
            Page<History> historyPage = deviceService.filterHistory(deviceId, status, startTime, endTime, pageable);

            Page<HistoryResponse> responsePage = historyPage.map(history ->
                    HistoryResponse.builder()
                            .id(history.getId().intValue())
                            .deviceId(history.getDevice().getId())
                            .deviceName(history.getDevice().getName())
                            .action(history.getAction())
                            .status(history.getStatus())
                            .timestamp(history.getTimestamp() != null ?
                                    history.getTimestamp().format(dateFormatter) : "N/A")
                            .build());

            return ResponseEntity.ok(ApiResponse.success(responsePage, "Lọc lịch sử thành công"));
        } catch (Exception e) {
            log.error("Lỗi lọc lịch sử: ", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("Lỗi lọc lịch sử", 500));
        }
    }
}
