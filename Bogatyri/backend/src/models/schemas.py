from pydantic import BaseModel

class FrequencyRequest(BaseModel):
    freq: int

class BeaconConfig(BaseModel):
    x: float
    y: float
    name: str

class BeaconRequest(BaseModel):
    beacons: list[BeaconConfig]

class Message(BaseModel):
    data: dict

class PositionResponse(BaseModel):
    x: float
    y: float
    accuracy: float

class Sensor(BaseModel):
    name: str
    rssi: int
    is_running: bool = True