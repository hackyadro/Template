from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class BeaconReading(BaseModel):
    """Данные измерения от одного маяка"""
    beaconId: str
    distance: float


class ScannerData(BaseModel):
    """Данные от устройства-сканера"""
    beaconReadings: List[BeaconReading]
    timestamp: Optional[float] = None


class Position(BaseModel):
    """Вычисленные координаты"""
    x: float
    y: float
    timestamp: Optional[float] = None
    accuracy: Optional[float] = None


class SessionConfig(BaseModel):
    """Конфигурация новой сессии"""
    frequency: float = 5.0


class SessionInfo(BaseModel):
    """Информация о сессии"""
    sessionId: str
    status: str
    startTime: float
    pointsCount: int = 0
    beaconsCount: int = 0


class WebSocketMessage(BaseModel):
    """Сообщение для WebSocket"""
    type: Literal["position_update", "session_status", "error"]
    sessionId: str
    position: Optional[Position] = None
    status: Optional[str] = None
    message: Optional[str] = None


# Вспомогательные модели для эндпоинтов
class StopSessionRequest(BaseModel):
    sessionId: str


class SavePathRequest(BaseModel):
    sessionId: str
    fileName: str
