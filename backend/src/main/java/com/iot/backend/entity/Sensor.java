package com.iot.backend.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "sensors")
public class Sensor {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    private String name;
    private String type;
    private String unit;
    private Integer pinGpio;

    @Column(name = "mqtt_key", unique = true)
    private String mqttKey;

    private String module;

    public Sensor() {}

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getType() { return type; }
    public void setType(String type) { this.type = type; }

    public String getUnit() { return unit; }
    public void setUnit(String unit) { this.unit = unit; }

    public Integer getPinGpio() { return pinGpio; }
    public void setPinGpio(Integer pinGpio) { this.pinGpio = pinGpio; }

    public String getMqttKey() { return mqttKey; }
    public void setMqttKey(String mqttKey) { this.mqttKey = mqttKey; }

    public String getModule() { return module; }
    public void setModule(String module) { this.module = module; }
}
