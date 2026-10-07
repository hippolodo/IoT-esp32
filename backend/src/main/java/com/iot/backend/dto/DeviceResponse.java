package com.iot.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO cho response thông tin thiết bị
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeviceResponse {
    private Integer id;
    private String name;
    private Integer pinGpio;
    private Integer status;  // 1 = ON, 0 = OFF
    private String updatedAt;
}
