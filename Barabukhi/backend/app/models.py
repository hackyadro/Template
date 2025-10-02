from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== PHP API Models (сохраняем совместимость) ====================

class MacRequest(BaseModel):
    """Запрос с MAC адресом"""
    mac: str = Field(..., pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')


class FreqResponse(BaseModel):
    """Ответ с частотой"""
    freq: int


class StatusRoadResponse(BaseModel):
    """Ответ со статусом записи маршрута"""
    write_road: bool


class MapResponse(BaseModel):
    """Ответ с данными карты"""
    map_name: str
    beacons: List[str]


class PingResponse(BaseModel):
    """Ответ на ping запрос"""
    change: bool
    change_list: List[str]


class SignalData(BaseModel):
    """Данные о сигнале от маяка"""
    name: str
    signal: int  # RSSI


class SendSignalRequest(BaseModel):
    """Запрос на отправку сигналов"""
    mac: str
    map_name: str
    list: List[SignalData]


class SendSignalResponse(BaseModel):
    """Ответ на отправку сигналов"""
    accept: bool


# ==================== Frontend API Models ====================

class BeaconInput(BaseModel):
    """Входные данные для создания маяка"""
    name: str
    x: float
    y: float


class BeaconResponse(BaseModel):
    """Ответ с данными маяка"""
    id: int
    map_id: int
    name: str
    x_coordinate: float
    y_coordinate: float
    created_at: datetime

    class Config:
        from_attributes = True


class MapCreateRequest(BaseModel):
    """Запрос на создание карты"""
    name: str
    beacons: List[BeaconInput]


class MapResponse2(BaseModel):
    """Ответ с полными данными карты"""
    id: int
    name: str
    created_at: datetime
    beacons: List[BeaconResponse]

    class Config:
        from_attributes = True


class DeviceCreateRequest(BaseModel):
    """Запрос на создание устройства"""
    name: str
    mac: str = Field(..., pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    map_id: Optional[int] = None
    poll_frequency: float = 1.0
    color: str = '#3b82f6'


class DeviceUpdateRequest(BaseModel):
    """Запрос на обновление устройства"""
    name: Optional[str] = None
    map_id: Optional[int] = None
    poll_frequency: Optional[float] = None
    color: Optional[str] = None


class DeviceResponse(BaseModel):
    """Ответ с данными устройства"""
    id: int
    name: str
    mac: str
    map_id: Optional[int]
    poll_frequency: float
    color: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PositionRequest(BaseModel):
    """Запрос на получение позиции устройства"""
    mac: str
    map_name: str


class PositionResponse(BaseModel):
    """Ответ с вычисленной позицией"""
    x: float
    y: float
    accuracy: Optional[float] = None
    algorithm: str = "trilateration"
    timestamp: datetime


class PathPoint(BaseModel):
    """Точка пути устройства"""
    x: float
    y: float
    accuracy: Optional[float] = None
    timestamp: datetime


class DevicePathResponse(BaseModel):
    """Ответ с историей пути устройства"""
    device_id: int
    device_name: str
    device_mac: str
    path: List[PathPoint]
