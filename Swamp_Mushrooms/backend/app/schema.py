from pydantic import BaseModel, Field, validator
from typing import List, Optional
from math import pi

class BeaconScanItem(BaseModel):
    beacon_id: str
    rssi: int

class ScanMessage(BaseModel):
    device_id: str
    scan: List[BeaconScanItem]
    timestamp_us: int
    seq: Optional[int] = None

class AnchorMeasurement(BaseModel):
    anchor_id: str
    anchor_x: float
    anchor_y: float
    angle: float
    angle_units: Optional[str] = "rad"
    angle_variance: Optional[float] = 0.0
    rssi: int
    timestamp_us: int
    seq: Optional[int] = None

    @validator("angle")
    def angle_range(cls, v):
        # if using degrees adapt or normalize
        if v < -2*pi or v > 2*pi:
            raise ValueError("angle seems out of range")
        return v
