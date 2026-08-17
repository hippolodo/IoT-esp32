package com.iot.backend.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "Sensors")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Sensor {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(nullable = false, length = 30)
    private String type; // temperature, humidity, light

    @Column(nullable = false, length = 10)
    private String unit; // °C, %, lux

    @Column(name = "pin_gpio", nullable = false)
    private Integer pinGpio;
}