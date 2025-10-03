import paho.mqtt.client as mqtt
import json
import time
import os
import csv
from utils.trilateration import Trilateration
from utils.polygon import simple_convex_hull

class PositioningEngine:
    def __init__(self):
        self.client = mqtt.Client(client_id="PositioningEngine")
        self.trilateration = Trilateration()
        self.current_position = {"x": 2.5, "y": 2.5}
        self.used_beacons = []
        self._smoothing_alpha = 0.3
        
        self.msg_buffer_count = 0
        self.msg_buffer: dict[str, dict[str, float]] = {}
        self.beacon_positions = self.load_beacon_positions()
        self.positioning_area = simple_convex_hull(
            tuple(map(lambda b: (b['x'], b['y']), self.beacon_positions.values()))
        )
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
                
                with open(beacons_file, "r", newline='') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        name, x, y = row["Name"].strip(), row["X"].strip(), row["Y"].strip()
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
                payload: dict[str, float] = json.loads(msg.payload.decode())
                print(f"📡 Received MQTT payload: {payload}")

                for key, value in payload.items():
                    if self.msg_buffer.get(key) == None:
                        self.msg_buffer[key] = dict()
                    
                    if self.msg_buffer[key].get("count") == None:
                        self.msg_buffer[key]["count"] = 0
                    
                    if self.msg_buffer[key].get("rssi_sum") == None:
                        self.msg_buffer[key]["rssi_sum"] = 0

                    self.msg_buffer[key]["count"] += 1
                    self.msg_buffer[key]["rssi_sum"] += value
                    self.msg_buffer_count += 1

                if self.msg_buffer_count < 3:
                    return
                
                avg_beacons_rssi: dict[str, float] = {}
                for b_name, b_values in self.msg_buffer.items():
                    avg_beacons_rssi[b_name] = b_values["rssi_sum"]/b_values["count"]
                
                self.msg_buffer_count = 0
                self.msg_buffer.clear()
                
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
                    position, used_beacons = self.trilateration.calculate_position(beacons_data, self.positioning_area)

                    print(f"📍 Position: {position}")
                    print(f"📍 Used beacons: {used_beacons}")
                    
                    if position:
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

        with open("etalon2.txt", "r") as f:
            msgs = f.read().split("\n\n")
            for msg in msgs:
                engine.on_message(None, None, MSG(msg))
                time.sleep(0.5)

        self.client.loop_forever()

class MSG:
    def __init__(self, payload: str):
        self.topic = "ble/beacons/raw"
        self.payload = payload.encode()

if __name__ == "__main__":
    engine = PositioningEngine()
    engine.start()
    