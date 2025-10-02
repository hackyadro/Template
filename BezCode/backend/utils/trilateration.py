import numpy as np
import math

class Trilateration:
    def __init__(self):
        self.tx_power = -46
        self.path_loss_exponent = 2.4
    
    def rssi_to_distance(self, rssi):
        if rssi >= -25: return 0.05
        if rssi <= -100: return 20.0
        
        distance = 10 ** ((self.tx_power - rssi) / (10 * self.path_loss_exponent))
        print(distance)
        return max(0.1, min(20.0, distance))
    
    def calculate_position(self, beacons_data):
        sorted_beacons = sorted(beacons_data, key=lambda x: x['rssi'], reverse=True)
        
        if len(sorted_beacons) < 3:
            return None
            
        beacons = sorted_beacons[:3]

        A = np.array([beacons[0]['position']['x'], beacons[0]['position']['y']])
        B = np.array([beacons[1]['position']['x'], beacons[1]['position']['y']])  
        C = np.array([beacons[2]['position']['x'], beacons[2]['position']['y']])
        
        rA = self.rssi_to_distance(beacons[0]['rssi'])
        rB = self.rssi_to_distance(beacons[1]['rssi'])
        rC = self.rssi_to_distance(beacons[2]['rssi'])
        
        result = self.three_circles_intersection(A, B, C, rA, rB, rC)
        
        if result:
            return {
                'x': round(float(result[0]), 2),
                'y': round(float(result[1]), 2)
            }
        
        return None
    
    def three_circles_intersection(self, A, B, C, rA, rB, rC):
        """
        Находит точку, ближайшую к пересечению трех окружностей
        используя метод наименьших квадратов
        """
        x1, y1 = A
        x2, y2 = B
        x3, y3 = C
        
        A_matrix = np.array([
            [2*(x2 - x1), 2*(y2 - y1)],
            [2*(x3 - x1), 2*(y3 - y1)]
        ])
        
        b_vector = np.array([
            rA**2 - rB**2 - x1**2 + x2**2 - y1**2 + y2**2,
            rA**2 - rC**2 - x1**2 + x3**2 - y1**2 + y3**2
        ])
        
        try:
            solution = np.linalg.lstsq(A_matrix, b_vector, rcond=None)[0]
            x, y = solution
            
            if not (np.isnan(x) or np.isnan(y) or np.isinf(x) or np.isinf(y)):
                return x, y
                
        except (np.linalg.LinAlgError, ValueError):
            return None
