#include "navigator/navigator.h"
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <unordered_map>
#include <algorithm>
#include <iostream>

using namespace message_objects;

namespace navigator {

void Navigator::setKnownBeacons(
    std::vector<message_objects::BLEBeacon> newBeacons) {
    knownBeacons_ = newBeacons;
}

// --- конструктор ---
Navigator::Navigator(const std::vector<BLEBeacon>& knownBeacons, double alpha,
                     double positionAlpha)
    : knownBeacons_(knownBeacons),
      alpha_(alpha),
      positionAlpha_(positionAlpha) {}

// --- calculatePosition ---
std::pair<double, double> Navigator::calculatePosition(
    const std::vector<BLEBeaconState>& beaconStates) {
    std::vector<std::pair<BLEBeacon, double>> distances;

    // Группируем измерения по именам маяков
    std::unordered_map<std::string, std::vector<double>> beaconDistances;
    
    for (const auto& state : beaconStates) {
        auto it = std::find_if(knownBeacons_.begin(), knownBeacons_.end(),
                               [&state](const BLEBeacon& b) {
                                   return b.name_ == state.name_;
                               });
        if (it == knownBeacons_.end())
            continue;

        double distance = rssiToDistance(state.rssi_, state.txPower_);
        if (distance > 0.1 && distance <= 50.0) { // Разумные пределы расстояния
            beaconDistances[state.name_].push_back(distance);
            // Отладочный вывод для проверки масштаба
            std::cout << "Beacon: " << state.name_ 
                     << ", RSSI: " << state.rssi_ 
                     << ", TxPower: " << state.txPower_
                     << ", Distance: " << distance << " m" << std::endl;
        }
    }

    // Обрабатываем каждый маяк
    for (const auto& [beaconName, measuredDistances] : beaconDistances) {
        if (measuredDistances.empty())
            continue;

        auto it = std::find_if(knownBeacons_.begin(), knownBeacons_.end(),
                               [&beaconName](const BLEBeacon& b) {
                                   return b.name_ == beaconName;
                               });
        if (it == knownBeacons_.end())
            continue;

        double filteredDistance;
        if (measuredDistances.size() == 1) {
            filteredDistance = measuredDistances[0];
        } else {
            std::vector<double> distances_copy = measuredDistances;
            filteredDistance = calculateMedian(distances_copy);
        }
        
        double smoothedDistance = updateMovingAverage(beaconName, filteredDistance);

        // Более мягкое ограничение скачка
        constexpr double maxJump = 8.0;
        auto prevIt = emaMap_.find(beaconName);
        if (prevIt != emaMap_.end() &&
            std::abs(smoothedDistance - prevIt->second) > maxJump) {
            // Не полностью игнорируем, а делаем промежуточное значение
            smoothedDistance = prevIt->second + 
                (smoothedDistance > prevIt->second ? maxJump : -maxJump);
        }

        distances.emplace_back(*it, smoothedDistance);
    }

    if (distances.size() < 3)
        throw std::runtime_error("Недостаточно маяков для триангуляции.");

    auto rawPos = trilateration(distances);

    return applyPositionEMA(rawPos);
}

// --- calculateMedian с IQR ---
double Navigator::calculateMedian(std::vector<double>& values) const {
    if (values.empty())
        throw std::runtime_error("Empty vector for median");

    std::sort(values.begin(), values.end());
    
    // Если мало данных, возвращаем простую медиану
    if (values.size() < 4) {
        size_t n = values.size() / 2;
        if (values.size() % 2 == 1)
            return values[n];
        else
            return (values[n - 1] + values[n]) / 2.0;
    }

    // Правильное вычисление квартилей
    size_t n = values.size();
    size_t q1_idx = n / 4;
    size_t q3_idx = 3 * n / 4;
    
    double q1 = values[q1_idx];
    double q3 = values[q3_idx];
    double iqr = q3 - q1;

    // Фильтруем выбросы только если IQR значимый
    std::vector<double> filtered;
    if (iqr > 0.1) {  // Избегаем деления на очень маленький IQR
        for (double v : values) {
            if (v >= q1 - 1.5 * iqr && v <= q3 + 1.5 * iqr)
                filtered.push_back(v);
        }
    }
    
    if (filtered.empty() || filtered.size() < values.size() / 2)
        filtered = values;  // Если отфильтровали слишком много, берем все

    size_t median_idx = filtered.size() / 2;
    if (filtered.size() % 2 == 1)
        return filtered[median_idx];
    else
        return (filtered[median_idx - 1] + filtered[median_idx]) / 2.0;
}

// --- updateMovingAverage ---
double Navigator::updateMovingAverage(const std::string& beaconName,
                                      double newValue) {
    auto it = emaMap_.find(beaconName);
    if (it == emaMap_.end()) {
        emaMap_[beaconName] = newValue;
        return newValue;
    } else {
        double& current = it->second;
        current = alpha_ * newValue + (1 - alpha_) * current;
        return current;
    }
}

// --- RSSI → расстояние (калиброванная формула для BLE) ---
double Navigator::rssiToDistance(int rssi, int txPower) const {
    if (rssi == 0) return -1.0; // Нет сигнала
    
    // Адаптивная обработка случая когда RSSI > txPower
    if (rssi > txPower) {
        // Вместо фиксированного 0.1, используем небольшое расстояние основанное на разности
        return 0.1 + (rssi - txPower) * 0.01;
    }
    
    // Калиброванная формула для реальных условий
    // Часто txPower указывается неточно, поэтому добавляем калибровочную константу
    constexpr double n = 2.5;      // Коэффициент затухания для офисных помещений с препятствиями
    constexpr double calibration = 5.0;  // Калибровочная константа (подбирается экспериментально)
    
    // Улучшенная формула с калибровкой
    double ratio = (double)(txPower + calibration - rssi) / (10.0 * n);
    double distance = std::pow(10.0, ratio);
    
    // Применяем дополнительный коэффициент масштабирования если нужно
    distance *= 0.8;  // Уменьшаем на 20% для компенсации переоценки
    
    // Ограничиваем разумными пределами
    return std::clamp(distance, 0.1, 50.0);
}

// --- EMA координат с адаптивным коэффициентом ---
std::pair<double, double> Navigator::applyPositionEMA(
    const std::pair<double, double>& newPos) const {
    if (!lastPositionInitialized_) {
        lastPosition_ = newPos;
        lastPositionInitialized_ = true;
        return newPos;
    }
    
    // Вычисляем расстояние до предыдущей позиции
    double dx = newPos.first - lastPosition_.first;
    double dy = newPos.second - lastPosition_.second;
    double distance = std::sqrt(dx * dx + dy * dy);
    
    // Адаптивный коэффициент: если изменение большое, доверяем меньше
    double alpha = positionAlpha_;
    if (distance > 5.0) {
        alpha = std::max(0.1, positionAlpha_ * (5.0 / distance));
    } else if (distance < 0.5) {
        alpha = std::min(0.9, positionAlpha_ * 1.5);
    }
    
    lastPosition_.first = alpha * newPos.first + (1 - alpha) * lastPosition_.first;
    lastPosition_.second = alpha * newPos.second + (1 - alpha) * lastPosition_.second;
    return lastPosition_;
}

// --- Триангуляция с равными весами ---
std::pair<double, double> Navigator::trilateration(
    std::vector<std::pair<BLEBeacon, double>>& distances) const {
    if (distances.size() < 3)
        throw std::runtime_error(
            "Недостаточно маяков для триангуляции (нужно минимум 3).");

    // Старт: центр масс маяков
    double x = 0, y = 0;
    for (auto& d : distances) {
        x += d.first.x_;
        y += d.first.y_;
    }
    x /= distances.size();
    y /= distances.size();

    // Улучшенный градиентный спуск с адаптивным шагом
    int maxIter = 500;
    double lr = 0.5;
    double tol = 1e-6;
    double decay = 0.99;  // Уменьшение шага обучения

    for (int iter = 0; iter < maxIter; ++iter) {
        double gx = 0, gy = 0;
        double totalWeight = 0;

        for (const auto& d : distances) {
            double dx = x - d.first.x_;
            double dy = y - d.first.y_;
            double dist = std::sqrt(dx * dx + dy * dy) + 1e-9;
            double err = dist - d.second;
            
            // Улучшенная весовая функция: обратно пропорционально квадрату расстояния
            double weight = 1.0 / (d.second * d.second + 0.1); // +0.1 для избежания деления на ноль
            totalWeight += weight;

            gx += weight * err * dx / dist;
            gy += weight * err * dy / dist;
        }

        if (totalWeight > 0) {
            gx /= totalWeight;
            gy /= totalWeight;
        }

        double stepSize = lr * std::exp(-decay * iter);
        x -= stepSize * gx;
        y -= stepSize * gy;

        // Проверка сходимости
        double gradNorm = std::sqrt(gx * gx + gy * gy);
        if (gradNorm < tol)
            break;
    }

    // Отладочный вывод результата триангуляции
    std::cout << "Trilateration result: (" << x << ", " << y << ") from " 
              << distances.size() << " beacons" << std::endl;
    for (const auto& d : distances) {
        std::cout << "  Beacon " << d.first.name_ << " at (" << d.first.x_ 
                  << ", " << d.first.y_ << ") distance: " << d.second << " m" << std::endl;
    }

    return {x, y};
}

}  // namespace navigator
