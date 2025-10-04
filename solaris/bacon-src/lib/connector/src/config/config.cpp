#include "config/config.h"
#include "message_objects/BLE.h"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <vector>

ConfigReader::ConfigReader(const std::string &filePath)
    : filePath_(filePath) {}

std::vector<message_objects::BLEBeacon> ConfigReader::readBeacons() const {
    std::vector<message_objects::BLEBeacon> beacons;

    std::ifstream file(filePath_);
    if (!file.is_open()) {
        throw std::runtime_error("Не удалось открыть файл конфигурации: " + filePath_);
    }

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty()) continue;

        std::stringstream ss(line);
        std::string name, xStr, yStr;

        if (!std::getline(ss, name, ';')) continue;
        if (!std::getline(ss, xStr, ';')) continue;
        if (!std::getline(ss, yStr, ';')) continue;

        try {
            double x = std::stod(xStr);
            double y = std::stod(yStr);
            beacons.push_back(message_objects::BLEBeacon{name, x, y});
        } catch (const std::exception&) {
            // если не удалось преобразовать в число — пропускаем строку
            continue;
        }
    }

    return beacons;
}
