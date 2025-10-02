import paho.mqtt.client as mqtt
import json
import time
import os
from utils.trilateration import Trilateration

class PositioningEngine:
    def __init__(self):
        self.client = mqtt.Client(client_id="PositioningEngine")
        self.trilateration = Trilateration()
        self.current_position = {"x": 2.5, "y": 2.5}
        self.used_beacons = []
        self._smoothing_alpha = 0.3
        
        self.beacon_positions = self.load_beacon_positions()
        print(f"✅ Positioning Engine initialized with {len(self.beacon_positions)} beacon positions")
    
    def load_beacon_positions(self):
        """Загружает позиции маяков из файла standart.beacons"""
        beacon_positions = {}
        beacons_file = "/app/data/standart.beacons"
        
        try:
            print(f"📁 Looking for beacon file: {beacons_file}")
            
            if os.path.exists(beacons_file) and os.path.isfile(beacons_file):
                print("✅ Beacon file found and is a file (not directory)")
                
                with open(beacons_file, 'r') as f:
                    lines = f.readlines()
                    print(f"📄 Read {len(lines)} lines from file")
                    
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if i == 0:  # Заголовок
                            print(f"📋 Header: {line}")
                            continue
                            
                        if line and ';' in line:
                            parts = line.split(';')
                            if len(parts) == 3:
                                name, x, y = parts
                                beacon_positions[name] = {
                                    'x': float(x),
                                    'y': float(y)
                                }
                                print(f"📌 Loaded beacon: {name} -> ({x}, {y})")

        except Exception as e:
            print(f"❌ Error loading beacon positions: {e}")
            import traceback
            traceback.print_exc()
        
        return beacon_positions
    
    
    def on_connect(self, client, userdata, flags, rc):
        print(f"✅ Positioning Engine Connected to MQTT Broker with code: {rc}")
        client.subscribe("ble/beacons/raw")
        print("📡 Subscribed to topic: ble/beacons/raw")
    
    def on_message(self, client, userdata, msg):
        if msg.topic == "ble/beacons/raw":
            try:
                payload = json.loads(msg.payload.decode())
                beacons = payload.get("beacons", [])
                
                print(f"📡 Received {len(beacons)} raw beacons")
                
                # Добавляем позиции к данным маяков
                beacons_with_positions = []
                for beacon in beacons:
                    beacon_name = beacon.get("name")
                    if beacon_name in self.beacon_positions:
                        beacon_with_position = beacon.copy()
                        beacon_with_position["position"] = self.beacon_positions[beacon_name]
                        beacons_with_positions.append(beacon_with_position)
                    else:
                        print(f"⚠️ Unknown beacon name: {beacon_name}")
                
                if len(beacons_with_positions) >= 3:
                    position, used_beacons = self.trilateration.calculate_position(beacons_with_positions)
                    
                    if position:
                        position['timestamp'] = time.time()
                        # Сглаживание
                        smoothed_x = (
                            self._smoothing_alpha * position['x'] +
                            (1 - self._smoothing_alpha) * self.current_position['x']
                        )
                        smoothed_y = (
                            self._smoothing_alpha * position['y'] +
                            (1 - self._smoothing_alpha) * self.current_position['y']
                        )
                        self.current_position = {
                            "x": round(smoothed_x, 2), 
                            "y": round(smoothed_y, 2), 
                            "timestamp": position['timestamp']
                        }
                        self.used_beacons = used_beacons
                        self.publish_position(self.current_position, used_beacons)
                    else:
                        print("❌ Trilateration calculation failed")
                else:
                    print(f"⚠️ Not enough beacons for positioning: {len(beacons_with_positions)}/3")
                    
            except Exception as e:
                print(f"❌ Error in on_message: {e}")

    def publish_position(self, position, used_beacons):
        """Публикует позицию и информацию о использованных маяках"""
        payload = {
            "x": position["x"],
            "y": position["y"],
            "timestamp": position["timestamp"],
            "used_beacons": [
                {
                    "name": b["name"],
                    "rssi": b["rssi"],
                    "position": b["position"],
                    "distance": round(self.trilateration.rssi_to_distance(b["rssi"]), 2)
                }
                for b in used_beacons
            ]
        }
        
        self.client.publish("navigation/position/current", json.dumps(payload))
        beacon_names = [b['name'] for b in used_beacons]
        print(f"📍 Published position: ({position['x']}, {position['y']}) using beacons: {beacon_names}")
    
    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        print("🚀 Starting Positioning Engine...")
        self.client.connect("mqtt-broker", 1883, 60)
        self.client.loop_forever()

if __name__ == "__main__":
    engine = PositioningEngine()
    engine.start()