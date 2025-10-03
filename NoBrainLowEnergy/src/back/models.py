from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    """Message types for MQTT communication"""
    SENSOR_DATA = "sensor_data"
    DEVICE_STATUS = "device_status"
    COMMAND = "command"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"

class QoSLevel(int, Enum):
    """MQTT Quality of Service levels"""
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2

class DeviceType(str, Enum):
    """Types of devices in the system"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CONTROLLER = "controller"

class MQTTMessage(BaseModel):
    """Model for MQTT message publishing"""
    topic: str = Field(..., description="MQTT topic to publish to")
    payload: Dict[str, Any] = Field(..., description="Message payload")
    qos: QoSLevel = Field(default=QoSLevel.AT_LEAST_ONCE, description="Quality of Service level")
    retain: bool = Field(default=False, description="Whether to retain the message")

class ReceivedMQTTMessage(BaseModel):
    """Model for received MQTT messages"""
    topic: str
    payload: Dict[str, Any]
    qos: int
    retain: bool
    timestamp: datetime
    client_id: Optional[str] = None

class MessageModel(BaseModel):
    """Generic message model"""
    message_id: Optional[str] = None
    message_type: MessageType
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]
    
class SensorData(BaseModel):
    """Model for sensor data"""
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    battery_level: Optional[float] = Field(None, ge=0, le=100)
    signal_strength: Optional[int] = Field(None, ge=-100, le=0)

class DeviceStatus(BaseModel):
    """Model for device status"""
    device_id: str
    device_type: DeviceType
    status: str = Field(..., description="online, offline, error, maintenance")
    last_seen: datetime
    firmware_version: Optional[str] = None
    battery_level: Optional[float] = Field(None, ge=0, le=100)
    uptime: Optional[int] = Field(None, description="Uptime in seconds")
    error_count: int = Field(default=0)
    
class DeviceCommand(BaseModel):
    """Model for device commands"""
    command_id: str
    device_id: str
    command: str
    parameters: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    priority: int = Field(default=1, ge=1, le=10)

class AlertMessage(BaseModel):
    """Model for alert messages"""
    alert_id: str
    device_id: str
    alert_type: str
    severity: str = Field(..., description="low, medium, high, critical")
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = Field(default=False)
    
class SystemStatus(BaseModel):
    """Model for system status"""
    total_devices: int
    online_devices: int
    offline_devices: int
    error_devices: int
    last_update: datetime
    mqtt_connected: bool
    uptime: int

class APIResponse(BaseModel):
    """Standard API response model"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
    pages: int


class BeaconPosition(BaseModel):
    """Single beacon position payload"""

    name: str = Field(..., alias="Name", description="Unique beacon identifier")
    x: float = Field(..., alias="X", description="Beacon X coordinate")
    y: float = Field(..., alias="Y", description="Beacon Y coordinate")

    class Config:
        allow_population_by_field_name = True
        anystr_strip_whitespace = True

    @validator("name")
    def _validate_name(cls, value: str) -> str:
        if not value:
            raise ValueError("Beacon name cannot be empty")
        return value

    def as_tuple(self) -> Tuple[float, float]:
        return float(self.x), float(self.y)


class BeaconConfig(BaseModel):
    """Beacon configuration upload payload"""

    positions: List[BeaconPosition]

    class Config:
        allow_population_by_field_name = True

class MQTTConnectionConfig(BaseModel):
    """MQTT connection configuration"""
    broker_host: str
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str
    use_tls: bool = False
    ca_cert_path: Optional[str] = None
    cert_file_path: Optional[str] = None
    key_file_path: Optional[str] = None
    tls_insecure: bool = False
    keepalive: int = 60