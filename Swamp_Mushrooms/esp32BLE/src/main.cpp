#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "BLEScanner.h"

// ==== Настройки WiFi и MQTT ====
const char* ssid = "POCO M5zzz";
const char* password = "22222222";
const char* mqtt_server = "172.16.11.232";
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/ble";
const char* device_id = "tracker_1";

// ==== Глобальные объекты ====
WiFiClient espClient;
PubSubClient mqttClient(espClient);
BLEScanner bleScanner;

int sentPackets = 0;

// ===== WiFi =====
void setupWiFi() {
    Serial.print("Connecting to WiFi: "); Serial.println(ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(200);
        Serial.print(".");
    }
    Serial.println("\n[WiFi] Connected. IP: " + WiFi.localIP().toString());
}

// ===== MQTT reconnect =====
bool reconnectMQTT() {
    if (mqttClient.connected()) return true;
    Serial.print("[MQTT] Connecting...");
    if (mqttClient.connect("ESP32-S3-BLE")) {
        Serial.println("OK");
        return true;
    } else {
        Serial.print("Failed rc=");
        Serial.println(mqttClient.state());
        return false;
    }
}

// ===== BLE обработчик пакета =====
void processBLE(const String& mac, const String& name, int rssi) {
    if (!mqttClient.connected()) return;

    DynamicJsonDocument doc(1024);
    doc["device_id"] = device_id;
    doc["timestamp_us"] = esp_timer_get_time();

    auto arr = doc.createNestedArray("scan");
    auto item = arr.createNestedObject();
    item["beacon_id"] = name;
    item["rssi"] = rssi;

    String out;
    serializeJson(doc, out);
    mqttClient.publish(mqtt_topic, out.c_str());
}

// ===== Setup =====
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("==== ESP32 BLE Continuous Scanner ====");
    setupWiFi();
    mqttClient.setServer(mqtt_server, mqtt_port);

    bleScanner.begin(processBLE); // запускаем BLE с обработчиком
}

// ===== Loop =====
void loop() {
    if (reconnectMQTT()) mqttClient.loop();
    // Всё остальное обрабатывается через callback
}
