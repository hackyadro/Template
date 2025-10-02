from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class BeaconBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    x_coordinate: float
    y_coordinate: float
    description: Optional[str] = None


class BeaconCreate(BeaconBase):
    pass


class Beacon(BeaconBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RSSIMeasurementBase(BaseModel):
    beacon_id: int
    rssi_value: int = Field(..., ge=-120, le=0)  # RSSI обычно от -120 до 0 dBm
    distance: Optional[float] = None


class RSSIMeasurementCreate(RSSIMeasurementBase):
    pass


class RSSIMeasurement(RSSIMeasurementBase):
    id: int
    measured_at: datetime

    class Config:
        from_attributes = True


class PositionBase(BaseModel):
    x_coordinate: float
    y_coordinate: float
    accuracy: Optional[float] = None
    algorithm: str = "trilateration"


class PositionCreate(PositionBase):
    pass


class Position(PositionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TrajectoryBase(BaseModel):
    session_id: UUID
    position_id: int
    sequence_number: int


class TrajectoryCreate(TrajectoryBase):
    pass


class Trajectory(TrajectoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PositionRequest(BaseModel):
    """Запрос для вычисления позиции на основе RSSI измерений"""
    measurements: list[RSSIMeasurementCreate]
    session_id: Optional[UUID] = None
    save_trajectory: bool = True


class PositionResponse(BaseModel):
    """Ответ с вычисленной позицией"""
    position: Position
    trajectory_id: Optional[int] = None
