import math

class SimpleKalmanRSSI:
    def __init__(self, process_variance=1e-3, measurement_variance=0.1, estimated_error=1.0):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.estimated_error = estimated_error
        self.current_estimate = 0.0
        self.is_initialized = False
    
    def update(self, measurement):
        if not self.is_initialized:
            self.current_estimate = measurement
            self.is_initialized = True
            return measurement
        
        # Предсказание
        temp_estimate = self.current_estimate
        temp_error = self.estimated_error + self.process_variance
        
        # Обновление
        kalman_gain = temp_error / (temp_error + self.measurement_variance)
        self.current_estimate = temp_estimate + kalman_gain * (measurement - temp_estimate)
        self.estimated_error = (1 - kalman_gain) * temp_error
        
        return self.current_estimate
    
    def reset(self):
        self.is_initialized = False
        self.estimated_error = 1.0
        self.current_estimate = 0.0