"""Request schemas for account and device endpoints."""
from pydantic import BaseModel, StrictInt


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
