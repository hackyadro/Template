from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== DEVICE API Models (BLE устройства) ====================

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
    signal: float  # RSSI


class SignalDataWithSamples(BaseModel):
    """Данные о сигнале от маяка с количеством измерений"""
    name: str
    signal: float  # RSSI
    samples: int = 1  # количество измерений


class SendSignalRequest(BaseModel):
    """Запрос на отправку сигналов"""
    mac: str
    map: str  # название карты
    list: List[SignalDataWithSamples]


class SendSignalResponse(BaseModel):
    """Ответ на отправку сигналов"""
    accept: bool


class SetMapToDeviceRequest(BaseModel):
    """Запрос на установку карты устройству"""
    mac: str
    map: str  # название карты


class SetMapToDeviceResponse(BaseModel):
    """Ответ на установку карты"""
    success: bool


class SetFreqRequest(BaseModel):
    """Запрос на установку частоты опроса"""
    mac: str
    freq: float


class SetFreqResponse(BaseModel):
    """Ответ на установку частоты"""
    success: bool


# ==================== Frontend API Models ====================

class BeaconInput(BaseModel):
    """Входные данные для создания маяка"""
    name: str
    x: float
    y: float


class AddMapRequest(BaseModel):
    """Запрос на добавление новой карты"""
    map: str  # название карты
    beacons: List[BeaconInput]


class AddMapResponse(BaseModel):
    """Ответ на добавление карты"""
    success: bool
    map_id: int


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
    mac: str = Field(..., pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    name: Optional[str] = None  # Если не указано, будет автоматически Device_{mac}
    map_id: Optional[int] = None
    poll_frequency: float = 1.0
    write_road: bool = True
    color: str = '#3b82f6'


class DeviceUpdateRequest(BaseModel):
    """Запрос на обновление устройства"""
    name: Optional[str] = None
    map_id: Optional[int] = None
    poll_frequency: Optional[float] = None
    write_road: Optional[bool] = None
    color: Optional[str] = None


class DeviceResponse(BaseModel):
    """Ответ с данными устройства"""
    id: int
    name: str
    mac: str
    map_id: Optional[int]
    poll_frequency: float
    write_road: bool
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
