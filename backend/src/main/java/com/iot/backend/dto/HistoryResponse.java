package com.iot.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO cho response lịch sử hành động
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class HistoryResponse {
    private Integer id;
    private Integer deviceId;
    private String deviceName;
    private String action;  // ON / OFF
    private String status;  // SUCCESS / FAILED / PENDING
    private String timestamp;
}
