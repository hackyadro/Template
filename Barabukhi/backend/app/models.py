from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


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
    beacons: list[str]


class PingResponse(BaseModel):
    """Ответ на ping запрос"""
    change: bool
    change_list: list[str]


class SignalData(BaseModel):
    """Данные о сигнале от маяка"""
    name: str
    signal: int


class SendSignalRequest(BaseModel):
    """Запрос на отправку сигналов"""
    mac: str
    map_name: str
    list: list[SignalData]


class SendSignalResponse(BaseModel):
    """Ответ на отправку сигналов"""
    accept: bool
