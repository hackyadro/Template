#pragma once
#include "message_objects/BLE.h"
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace navigator {

class Navigator {
   public:
    // Конструктор принимает список известных маяков и коэффициент сглаживания для расстояний
    Navigator(const std::vector<message_objects::BLEBeacon>& knownBeacons,
              double alpha = 0.5, double positionAlpha = 0.25);

    void setKnownBeacons(std::vector<message_objects::BLEBeacon> newBeacons);

    // Принимает список состояний маяков, возвращает сглаженные координаты  
    std::pair<double, double> calculatePosition(
        const std::vector<message_objects::BLEBeaconState>& beaconStates);
    
    // Калибровка масштаба расстояний
    void setDistanceCalibration(double calibrationFactor, double scaleFactor = 1.0);

   private:
    // Список известных маяков
    std::vector<message_objects::BLEBeacon> knownBeacons_;

    // Коэффициент EMA для расстояний
    double alpha_;

    // Коэффициент EMA для координат
    double positionAlpha_;

    // Карта "имя маяка → сглаженное значение расстояния"
    mutable std::unordered_map<std::string, double> emaMap_;

    // Последняя вычисленная позиция для EMA координат
    mutable std::pair<double, double> lastPosition_;
    mutable bool lastPositionInitialized_ = false;

    // Калибровочные параметры
    double calibrationFactor_ = 5.0;  // Калибровочная константа
    double scaleFactor_ = 0.8;        // Коэффициент масштабирования

    // Преобразование RSSI → расстояние
    double rssiToDistance(int rssi, int txPower) const;

    // Фильтрация и медиана с IQR
    double calculateMedian(std::vector<double>& values) const;

    // Адаптивный EMA для расстояний
    double updateMovingAverage(const std::string& beaconName, double newValue);

    // EMA на координаты
    std::pair<double, double> applyPositionEMA(
        const std::pair<double, double>& newPos) const;

    // Триангуляция по сглаженным расстояниям (взвешенная)
    std::pair<double, double> trilateration(
        std::vector<std::pair<message_objects::BLEBeacon, double>>& distances)
        const;
};

}  // namespace navigator
