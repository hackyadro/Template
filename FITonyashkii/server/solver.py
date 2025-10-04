from typing import Dict, Optional, Iterable


class Solver:
    def __init__(self, beacons: Iterable, tx: int = -65, n: float = 1.0):
        self.beacons = {
            beacon.name: (float(beacon.x), float(beacon.y)) for beacon in beacons
        }
        self.tx = tx
        self.n = n

    def get_position(self, rssies: Dict):
        # sorted_beacons = sorted(
        #     rssies.items(),
        #     key=lambda x: x[1],
        #     reverse=True
        # )[:3]
        total_weight = 0
        weighted_x = 0
        weighted_y = 0

        for beacon_name, beacon_rssi in rssies.items():
            x, y = self.beacons[beacon_name]
            distance = float(self.get_distance(beacon_rssi))
            # Use inverse distance as weight (closer beacons have more influence)
            weight = 1.0 / (distance + 0.05)  # Add small value to avoid division by zero
            weighted_x += x * weight
            weighted_y += y * weight
            total_weight += weight

        estimated_x = weighted_x / total_weight
        estimated_y = weighted_y / total_weight
        return estimated_x, estimated_y

    def get_distance(self, rssi: float) -> float:
        return float(10 ** ((float(self.tx) - float(rssi)) / (10.0 * float(self.n))))
