from dataclasses import dataclass
from typing import Dict
from rssi_filter import KalmanFilterManager
from solver import Solver

@dataclass
class BeaconData:
    name: str
    x: float
    y: float


@dataclass
class MapObject:
    name: str
    x: int = 0
    y: int = 0
    rssi: int = 0


class RSSILocator:
    def __init__(self, beacons: list[BeaconData]):
        self.beacons = beacons
        self.beacon_names = set(b.name for b in beacons)
        self.kalman_manager = KalmanFilterManager()
        self.solver = Solver(beacons)
        self.filtered_rssi: Dict[str, int] = {}
        self.x = 0
        self.y = 0

    def get_map_data(self) -> list[MapObject]:
        return [MapObject(name=b.name, x=b.x, y=b.y, rssi=self.filtered_rssi.get(b.name, 0)) for b in self.beacons]

    def update_beacons(self, beacons: list[BeaconData]):
        self.beacons = beacons
        self.beacon_names = set(b.name for b in beacons)
        self.solver = Solver(beacons)
    
    def calibrate(self, x: float, y: float):
        print(f"Calibrating with position: ({x}, {y})")

    def on_data(self, device_name: str, rssi: int, tx_power: int = -46):
        if device_name not in self.beacon_names:
            return 
        
        filtered_value = self.kalman_manager.apply_kalman_filter(device_name, rssi)
        self.filtered_rssi[device_name] = filtered_value[0]

        if len(self.filtered_rssi) >= 1:
            position = self.solver.get_position(self.filtered_rssi)
            # print(position)
            if position:
                self.x = 0.9 * self.x + 0.1*position[0]
                self.y = 0.9 * self.y + 0.1*position[1]
