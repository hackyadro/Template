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

    beacons = [
        {"mac": "AA:BB:CC:DD:EE:01", "position": {"x": 0, "y": 0}, "name": "Beacon 1"},
        {"mac": "AA:BB:CC:DD:EE:02", "position": {"x": 5, "y": 0}, "name": "Beacon 2"},
        {"mac": "AA:BB:CC:DD:EE:03", "position": {"x": 2.5, "y": 5}, "name": "Beacon 3"}
    ]

    angle = 0
    while True:
        x = 2.5 + 2.0 * math.cos(angle)
        y = 2.5 + 2.0 * math.sin(angle)
        angle += 0.15
        
        beacons_data = []
        for beacon in beacons:
            distance = math.sqrt((x - beacon['position']['x'])**2 + (y - beacon['position']['y'])**2)
            rssi = -46 - 10 * 2.4 * math.log10(distance) if distance > 0.1 else -35
            rssi += random.uniform(-5, 5)
            rssi = max(-100, min(-30, rssi))
            
            beacons_data.append({
                'mac': beacon['mac'],
                'rssi': int(rssi),
                'position': beacon['position'],
                'name': beacon['name'],
                'timestamp': time.time()
            })
        
        mqtt_payload = {
            'beacons': beacons_data,
            'timestamp': time.time(),
            'source': 'simulator'
        }
        
        client.publish("ble/beacons/raw", json.dumps(mqtt_payload))
        print(f"📡 Simulated: ({x:.2f}, {y:.2f}) - {len(beacons_data)} beacons")
        
        time.sleep(0.2)

except Exception as e:
    print(f"❌ Error: {e}")
    time.sleep(10)