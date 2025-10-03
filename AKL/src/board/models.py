import ujson as json

class BLData():
    def __init__(self, name: str, rssi: int):
        self.name = name
        self.rssi = rssi
        self.index = int(name.split("_")[1])
        
    def __repr__(self):
        return f"{self.name}, {self.rssi}"
    
    def to_dict(self):
        return {"name" : self.name, "rssi" : self.rssi}
    def get_index(self):
        return self.index
    
def bl_list_to_json(data: list[BLData]) -> str:
    dict_data = []
    for i in data:
        dict_data.append(i.to_dict())
    res = json.dumps(dict_data)
    return res
    
