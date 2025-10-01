from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # SSL/TLS Settings for API
    USE_SSL: bool = False
    SSL_CERT_FILE: str = ""
    SSL_KEY_FILE: str = ""
    
    # MQTT Broker Settings
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 8883  # Default secure port
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "fastapi_backend"
    
    # MQTT TLS Settings
    MQTT_USE_TLS: bool = True
    MQTT_CA_CERT_PATH: str = "certs/ca.crt"
    MQTT_CERT_FILE_PATH: str = "certs/client.crt"
    MQTT_KEY_FILE_PATH: str = "certs/client.key"
    MQTT_TLS_INSECURE: bool = False  # Set to True for self-signed certs
    
    # MQTT Topic Settings
    MQTT_BASE_TOPIC: str = "nobrainlowenergy"
    MQTT_DEVICE_TOPIC: str = "nobrainlowenergy/devices"
    MQTT_STATUS_TOPIC: str = "nobrainlowenergy/status"
    MQTT_COMMAND_TOPIC: str = "nobrainlowenergy/commands"
    
    # Database Settings (for future use)
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()