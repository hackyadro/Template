from easy_trilateration.model import Circle
from easy_trilateration.least_squares import easy_least_squares
from utils.polygon import move_point_inside

class Trilateration:
    def __init__(self):
        self.tx_power = -46
        self.path_loss_exponent = 2.2
    
    def rssi_to_distance(self, rssi):
        return 11.8099735 ** ((self.tx_power - rssi) / (10 * self.path_loss_exponent))
    
    def calculate_position(self, beacons_data, positioning_area):
        """Возвращает позицию и использованные маяки"""

        _MIN_BEACON_COUNT = 3
        _CALC_BEACON_COUNT = 3

        if len(beacons_data) < _MIN_BEACON_COUNT:
            return None, []
            
        used_beacons = sorted(beacons_data, key=lambda x: x['rssi'], reverse=True)[:_CALC_BEACON_COUNT]

        circles = [
            Circle(
                b['position']['x'],
                b['position']['y'],
                self.rssi_to_distance(b['rssi'])
            ) for b in used_beacons
        ]
        
        # avg = [
        #     sum(map(lambda x: x['position']['x'], used_beacons))/_CALC_BEACON_COUNT,
        #     sum(map(lambda x: x['position']['y'], used_beacons))/_CALC_BEACON_COUNT
        # ]

        sph, result = easy_least_squares(circles)
        result = result.x
        
        # results = []
        # for i in range(200):
        #     try:
        #         sph, result = easy_least_squares(circles)
        #         cr = 10
        #         if result.success and (abs(result.x[0] - avg[0]) < cr and abs(result.x[1] - avg[1]) < cr):
        #             results.append(result.x)
        #     except Exception as e:
        #         print(f"Ошибка в итерации {i+1}: {e}")
        #         continue
        
        # # Если нет успешных результатов, возвращаем None
        # if not results:
        #     return None, beacons
        
        # Находим среднее значение по всем успешным итерациям
        # results_array = np.array(results)
        # avg_result = np.mean(results_array, axis=0)
        
        position = (float(result[0]), float(result[1]))
        position = move_point_inside(position, positioning_area)

        return position, used_beacons
        
        #return None, []