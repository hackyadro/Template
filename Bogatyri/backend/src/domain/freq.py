from pydantic import BaseModel

class FrequencyRequest(BaseModel):
    freq: int