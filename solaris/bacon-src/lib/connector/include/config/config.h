#pragma once

#include <string>
#include <vector>

#include "message_objects/BLE.h" // здесь у тебя объявлен struct BLEBeacon

class ConfigReader {
public:
    explicit ConfigReader(const std::string &filePath);

    // Читает конфиг и возвращает список маяков
    std::vector<message_objects::BLEBeacon> readBeacons() const;

private:
    std::string filePath_;
};
