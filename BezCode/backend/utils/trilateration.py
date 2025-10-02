import numpy as np
import math
from easy_trilateration.model import Circle
from easy_trilateration.least_squares import easy_least_squares


class Trilateration:
    def __init__(self):
        self.tx_power = -46
        self.path_loss_exponent = 2.2
    
    def rssi_to_distance(self, rssi):
        if rssi >= -25: return 0.05
        if rssi <= -100: return 20.0
        
        distance = 11.8099735 ** ((self.tx_power - rssi) / (10 * self.path_loss_exponent))
        return max(0.1, min(20.0, distance))
    
    def calculate_position(self, beacons_data):
        """Возвращает позицию и использованные маяки"""
        sorted_beacons = sorted(beacons_data, key=lambda x: x['rssi'], reverse=True)
        
        if len(sorted_beacons) < 3:
            return None, []
            
        beacons = sorted_beacons[:3]

        A = np.array([beacons[0]['position']['x'], beacons[0]['position']['y']])
        B = np.array([beacons[1]['position']['x'], beacons[1]['position']['y']])  
        C = np.array([beacons[2]['position']['x'], beacons[2]['position']['y']])
        # D = np.array([beacons[3]['position']['x'], beacons[3]['position']['y']])
        circle1 = Circle(x=beacons[0]['position']['x'], y=beacons[0]['position']['y'], r= self.rssi_to_distance(beacons[0]['rssi']))
        circle2 = Circle(x=beacons[1]['position']['x'], y=beacons[1]['position']['y'], r=self.rssi_to_distance(beacons[1]['rssi']))
        circle3 = Circle(x=beacons[2]['position']['x'], y=beacons[2]['position']['y'], r=self.rssi_to_distance(beacons[2]['rssi']))
        # circle4 = Circle(x=beacons[3]['position']['x'], y=beacons[3]['position']['y'], r=self.rssi_to_distance(beacons[3]['rssi']))

        circles = [circle1, circle2, circle3]

        avg = [
            A[0]+B[0]+C[0]/3,
            A[1]+B[1]+C[1]/3
        ]

        # sph, result= easy_least_squares(circles)
        # result = result.x
        results = []
        for i in range(150):
            try:
                sph, result = easy_least_squares(circles)
                cr = 10
                if result.success and abs(result.x[0] - avg[0]) < cr and abs(result.x[1] - avg[1]) < cr:
                    results.append(result.x)
            except Exception as e:
                print(f"Ошибка в итерации {i+1}: {e}")
                continue
        
        # Если нет успешных результатов, возвращаем None
        if not results:
            return None, beacons
        
        # Находим среднее значение по всем успешным итерациям
        results_array = np.array(results)
        avg_result = np.mean(results_array, axis=0)
        
        position = {
            'x': round(float(avg_result[0]), 2),
            'y': round(float(avg_result[1]), 2)
        }
        return position, beacons
        
        #return None, []
    
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