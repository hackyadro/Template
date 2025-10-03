#pragma once
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <functional>

// Тип обработчика найденного устройства
using BLEHandler = std::function<void(const String& mac, const String& name, int rssi)>;

class BLEScannerCallbacks : public BLEAdvertisedDeviceCallbacks {
public:
    BLEHandler handler;

    BLEScannerCallbacks(BLEHandler h) : handler(h) {}

    void onResult(BLEAdvertisedDevice advertisedDevice) override {
        String mac = advertisedDevice.getAddress().toString().c_str();
        String name = advertisedDevice.haveName() ? advertisedDevice.getName().c_str() : "unknown";
        int rssi = advertisedDevice.getRSSI();

        // Сразу вызываем обработчик
        handler(mac, name, rssi);
    }
};

class BLEScanner {
public:
    BLEScanner() {}
    void begin(BLEHandler handler) {
        BLEDevice::init("");
        pBLEScan = BLEDevice::getScan();
        pBLEScan->setActiveScan(true);
        pBLEScan->setInterval(160);
        pBLEScan->setWindow(160);
        pBLEScan->setAdvertisedDeviceCallbacks(new BLEScannerCallbacks(handler), true);
        pBLEScan->start(0, nullptr, false); // бесконечный асинхронный скан
        Serial.println("[BLE] Scanner initialized");
    }

private:
    BLEScan* pBLEScan;
};
