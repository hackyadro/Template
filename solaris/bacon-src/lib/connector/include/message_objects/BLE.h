#pragma once

#include <string>

namespace message_objects {
    struct BLEBeacon {
        std::string name_;
        double x_;
        double y_;
    };

    struct BLEBeaconState {
        std::string name_;
        int rssi_;
        int txPower_;
    };
}; // namespace message_objects
