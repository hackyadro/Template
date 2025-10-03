from pydantic import BaseModel

class Sensor(BaseModel):
    name: str
    rssi: int
    is_running: bool = True