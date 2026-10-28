import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "mysql+pymysql://root:@127.0.0.1:3306/iot_db?charset=utf8mb4"))
    mqtt_enabled: bool = field(default_factory=lambda: os.getenv("MQTT_ENABLED", "true").lower() == "true")
    mqtt_host: str = field(default_factory=lambda: os.getenv("MQTT_HOST", "127.0.0.1"))
    mqtt_port: int = field(default_factory=lambda: int(os.getenv("MQTT_PORT", "1884")))
    mqtt_username: str = field(default_factory=lambda: os.getenv("MQTT_USERNAME", ""))
    mqtt_password: str = field(default_factory=lambda: os.getenv("MQTT_PASSWORD", ""))
    sensor_topic: str = field(default_factory=lambda: os.getenv("MQTT_SENSOR_TOPIC", "esp32/sensor/data"))
    device_map: dict[int, str] = field(default_factory=lambda: {
        int(key): value for key, value in json.loads(os.getenv(
            "MQTT_DEVICE_MAP", '{"1":"led1","2":"led2","3":"led3"}')).items()})
    command_timeout: int = field(default_factory=lambda: int(os.getenv("COMMAND_TIMEOUT_SECONDS", "15")))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","))

    def __post_init__(self):
        if not set(self.device_map.values()) <= {"led1", "led2", "led3"}:
            raise ValueError("MQTT_DEVICE_MAP chỉ hỗ trợ led1, led2 và led3")
        if len(set(self.device_map.values())) != len(self.device_map):
            raise ValueError("Mỗi LED phải ánh xạ tới một device ID riêng")
        if self.command_timeout <= 0:
            raise ValueError("COMMAND_TIMEOUT_SECONDS phải lớn hơn 0")
