"""Request schemas for account and device endpoints."""
from pydantic import BaseModel, StrictInt, Field


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class RegisterRequest(BaseModel):
    username: str
    fullName: str
    email: str
    password: str
    confirmPassword: str


class DeviceControlRequest(BaseModel):
    deviceId: StrictInt
    status: StrictInt


class ThresholdRequest(BaseModel):
    temperature: float = Field(ge=0, le=50, allow_inf_nan=False, strict=True)
    humidity: float = Field(ge=0, le=100, allow_inf_nan=False, strict=True)
    light: float = Field(ge=0, le=4095, allow_inf_nan=False, strict=True)
