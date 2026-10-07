package com.iot.backend.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO cho request điều khiển thiết bị
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeviceControlRequest {
    private Integer deviceId;
    private Integer status;  // 1 = ON, 0 = OFF
}
