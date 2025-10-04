## Requirements
- **CMake** 3.16
- **C++17**
- libs: **MQTT**

## Install **MQTT** in Ubuntu:
1. `sudo apt-get install libpaho-mqtt-dev`
2. `git clone https://github.com/eclipse-paho/paho.mqtt.cpp.git`
3. `cd paho.mqtt.cpp`
4. `cmake -Bbuild -H. -DPAHO_WITH_SSL=ON`
5. `cmake --build build --target install`
