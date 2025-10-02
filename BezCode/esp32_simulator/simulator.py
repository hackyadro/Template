import paho.mqtt.client as mqtt
import json
import time
import math
import random

print("🚀 Starting ESP32 Simulator...")

try:
    client = mqtt.Client(client_id="ESP32Simulator")
    client.connect("mqtt-broker", 1883, 60)
    client.loop_start()
    print("✅ Connected to MQTT broker")

    # Используем имена из standart.beacons
    beacon_names = ["beacon_1", "beacon_2", "beacon_3", "beacon_4", "beacon_5"]

    angle = 0
    counter = 0
    
    while True:
        # Симулируем движение по кругу
        x = 2.5 + 1.5 * math.cos(angle)
        y = 2.5 + 1.5 * math.sin(angle)
        angle += 0.1
        
        # Выбираем случайные маяки
        active_beacons = random.sample(beacon_names, random.randint(3, 5))
        beacons_data = []
        
        for beacon_name in active_beacons:
            # Реалистичный RSSI based on distance from center
            base_rssi = -50
            rssi_variation = random.randint(-5, 5)
            rssi = base_rssi + rssi_variation
            
            beacons_data.append({
                'name': beacon_name,
                'rssi': rssi,
                'timestamp': time.time()
            })
        
        mqtt_payload = {
            'beacons': beacons_data,
            'timestamp': time.time(),
            'source': 'simulator'
        }
        
        client.publish("ble/beacons/raw", json.dumps(mqtt_payload))
        counter += 1
        print(f"📡 [{counter}] Simulated position: ({x:.2f}, {y:.2f}) - Beacons: {[b['name'] for b in beacons_data]}")
        
        time.sleep(2)

except Exception as e:
    print(f"❌ Simulator error: {e}")
    import traceback
    traceback.print_exc()
    time.sleep(10)