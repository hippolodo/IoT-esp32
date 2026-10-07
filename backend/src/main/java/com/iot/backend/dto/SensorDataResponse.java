package com.iot.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO cho response dữ liệu cảm biến
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SensorDataResponse {
    private Long id;
    private Integer sensorId;
    private String sensorName;
    private String sensorType;
    private String unit;
    private Float value;
    private String recordedAt;
}
