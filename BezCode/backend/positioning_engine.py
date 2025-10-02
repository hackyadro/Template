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
        print(f"📋 Available beacons: {list(self.beacon_positions.keys())}")
    
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
                                beacon_positions[name.strip()] = {
                                    'x': float(x.strip()),
                                    'y': float(y.strip())
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
                print(f"📡 Received MQTT payload: {payload}")
                
                # Обрабатываем новый формат: {"beacon_1": -45, "beacon_2": -50, ...}
                beacons_data = []
                
                for beacon_name, rssi in payload.items():
                    if beacon_name in self.beacon_positions:
                        beacon_data = {
                            "name": beacon_name,
                            "rssi": rssi,
                            "position": self.beacon_positions[beacon_name]
                        }
                        beacons_data.append(beacon_data)
                        print(f"📍 Mapped {beacon_name}: RSSI {rssi} -> Position ({beacon_data['position']['x']}, {beacon_data['position']['y']})")
                    else:
                        print(f"⚠️ Unknown beacon name in payload: {beacon_name}")
                
                print(f"📍 Total beacons with known positions: {len(beacons_data)}")
                
                if len(beacons_data) >= 3:
                    position, used_beacons = self.trilateration.calculate_position(beacons_data)

                    print(f"📍 Position: {position}")
                    print(f"📍 Used beacons: {used_beacons}")
                    
                    if position:
                        position['timestamp'] = time.time()
                        # Сглаживание
                        # smoothed_x = (
                        #     self._smoothing_alpha * position['x'] +
                        #     (1 - self._smoothing_alpha) * self.current_position['x']
                        # )
                        # smoothed_y = (
                        #     self._smoothing_alpha * position['y'] +
                        #     (1 - self._smoothing_alpha) * self.current_position['y']
                        # )
                        self.current_position = {
                            "x": round(position['x'], 2), 
                            "y": round(position['y'], 2), 
                            "timestamp": position['timestamp']
                        }
                        self.used_beacons = used_beacons
                        self.publish_position(self.current_position, used_beacons)
                    else:
                        print("❌ Trilateration calculation failed")
                else:
                    print(f"⚠️ Not enough beacons for positioning: {len(beacons_data)}/3")
                    
            except Exception as e:
                print(f"❌ Error in on_message: {e}")
                import traceback
                traceback.print_exc()

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
    