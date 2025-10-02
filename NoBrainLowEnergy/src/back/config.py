from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings (only internal defaults - no env-driven connection data)"""
    
    # Application-internal defaults (not read from env by other parts of the app)
    DATABASE_URL: str = "sqlite:///./app.db"
    LOG_LEVEL: str = "INFO"
    
    # MQTT topic constants (logical names, not connection parameters)
    MQTT_BASE_TOPIC: str = "nobrainlowenergy"
    MQTT_DEVICE_TOPIC: str = "nobrainlowenergy/devices"
    MQTT_STATUS_TOPIC: str = "nobrainlowenergy/status"
    MQTT_COMMAND_TOPIC: str = "nobrainlowenergy/commands"
    MQTT_CLIENT_ID: str = "nobrainlowenergy_backend"
    
    # In pydantic v2 / pydantic-settings, use model_config to allow/ignore extra env vars.
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",  # ignore env vars that are not declared on the model
    }

# Create global settings instance
settings = Settings()