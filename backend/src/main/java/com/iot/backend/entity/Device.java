package com.iot.backend.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.UpdateTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "devices")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Device {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(name = "pin_gpio", nullable = false)
    private Integer pinGpio;

    @Column(nullable = false)
    private Integer status; // 0: OFF, 1: ON

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}