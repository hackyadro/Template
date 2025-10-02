"""
MQTT Bridge - заглушка для ESP32 симулятора
В реальном проекте здесь будет код для приема данных с ESP32
"""
import paho.mqtt.client as mqtt
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MQTTBridge")

class MQTTBridge:
    def __init__(self):
        self.client = mqtt.Client("MQTTBridge")
        
    def on_connect(self, client, userdata, flags, rc):
        logger.info("MQTT Bridge connected to broker")
        
    def start(self):
        self.client.on_connect = self.on_connect
        self.client.connect("mqtt-broker", 1883, 60)
        self.client.loop_start()
        logger.info("MQTT Bridge started")
        
        while True:
            time.sleep(1)

if __name__ == "__main__":
    bridge = MQTTBridge()
    bridge.start()