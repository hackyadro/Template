from typing import Dict, Any
import numpy as np
from filterpy.kalman import KalmanFilter


class KalmanFilterManager:
    def __init__(self):
        self.filters: Dict[str, Any] = {}
        self.measurement_uncertainty = 100

    def initialize_kalman_filter(self):
        # Initialize the Kalman Filter
        kf = KalmanFilter(dim_x=1, dim_z=1)
        kf.x = np.array([0.0])  # initial state
        kf.F = np.array([[1.0]])  # state transition matrix
        kf.H = np.array([[1.0]])  # Measurement function
        kf.P *= 1000.0  # covariance matrix
        kf.R = self.measurement_uncertainty  # state uncertainty
        return kf

    def get_or_create_filter(self, beacon_name: str):
        if beacon_name not in self.filters:
            self.filters[beacon_name] = self.initialize_kalman_filter()
        return self.filters[beacon_name]

    def apply_kalman_filter(self, beacon_name: str, new_rssi_value: int):
        kf = self.get_or_create_filter(beacon_name)
        # Use the Kalman Filter for the new value
        kf.predict()
        kf.update(np.array([new_rssi_value]))
        return kf.x  # This is the filtered value
    
