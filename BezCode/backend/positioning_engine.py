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
        self._current_max_delta = 2.0
        self.beacon_positions = {}
        self.positioning_area = None

        self.msg_buffer_count = 0
        self.msg_buffer: dict[str, dict[str, float]] = {}
    
    def on_connect(self, client, userdata, flags, rc):
        print(f"Positioning Engine Connected to MQTT Broker with code: {rc}")
        client.subscribe("ble/beacons/raw")
        client.subscribe("navigation/route/control")
        client.subscribe("beacons/management/setConf")
        print("Subscribed to topics: ble/beacons/raw, navigation/route/control, beacons/management/setConf")
    
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

                if self.msg_buffer_count < 10:
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
                        print(f"Mapped {beacon_name}: RSSI {rssi} -> Position ({beacon_data['position']['x']}, {beacon_data['position']['y']})")
                    else:
                        print(f"Unknown beacon name in payload: {beacon_name}")
                
                print(f"Total beacons with known positions: {len(beacons_data)}")
                
                if len(beacons_data) >= 3:
                    position, used_beacons = self.trilateration.calculate_position(beacons_data, self.positioning_area)

                    print(f"Position: {position}")
                    print(f"Used beacons: {used_beacons}")
                    
                    if position:
                        delta_x = position['x'] - self.current_position['x']
                        delta_y = position['y'] - self.current_position['y']
                        distance = (delta_x**2 + delta_y**2)**0.5
                        
                        
                        base_max_delta = 2.0  # Базовое максимальное смещение
                        acceleration_factor = 1  # Коэффициент ускорения
                        decay_factor = 1  # Коэффициент замедления
                        
                        
                        if distance > self._current_max_delta:
                            
                            self._current_max_delta = min(10.0, self._current_max_delta * (1 + acceleration_factor))
                            
                            scale_factor = self._current_max_delta / distance
                            position['x'] = self.current_position['x'] + delta_x * scale_factor
                            position['y'] = self.current_position['y'] + delta_y * scale_factor
                            print(f"Сглажено сильное смещение: {distance:.2f} > {self._current_max_delta:.2f}")
                            print(f"Увеличена максимальная дельта до: {self._current_max_delta:.2f}")
                        else:
                            self._current_max_delta = max(base_max_delta, self._current_max_delta * decay_factor)
                        self.current_position = {
                            "x": round(position['x'], 2), 
                            "y": round(position['y'], 2), 
                        }
                        self.used_beacons = used_beacons
                        self.publish_position(self.current_position, used_beacons)
                    else:
                        print("Trilateration calculation failed")
                else:
                    print(f"Not enough beacons for positioning: {len(beacons_data)}/3")
                    
            except Exception as e:
                print(f"Error in on_message: {e}")
                import traceback
                traceback.print_exc()
        elif msg.topic == "navigation/route/control":
            try:
                payload = json.loads(msg.payload.decode())
                command = payload.get("command")
                print(f"Received route control command: {command}")
                
                if command == "start_routing":
                    print("Starting navigation route...")
                elif command == "stop_routing":
                    print("Stop navigation route...")
                
            except Exception as e:
                print(f"Error processing route control command: {e}")
        elif msg.topic == "beacons/management/setConf":
            try:
                payload = json.loads(msg.payload.decode())
                print(f"Received new beacon configuration: {payload}")
                
                # Update the beacon configuration
                if "beacons" in payload:
                    self.beacon_positions = payload["beacons"]
                    if self.beacon_positions:
                        beacon_coords = [(beacon['x'], beacon['y']) for beacon in self.beacon_positions.values()]
                        print(beacon_coords)
                        self.positioning_area = simple_convex_hull(tuple(beacon_coords))
                    print(f"Updated beacon configuration with {len(self.beacon_positions)} beacons")
                    print(f"New available beacons: {list(self.beacon_positions.keys())}")
                else:
                    print("Invalid beacon configuration format")
            except Exception as e:
                print(f"Error updating beacon configuration: {e}")
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
        print(f"Published position: ({position['x']}, {position['y']}) using beacons: {beacon_names}")
    
    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        print("Starting Positioning Engine...")
        self.client.connect("mqtt-broker", 1883, 60)

        self.client.loop_forever()

class MSG:
    def __init__(self, payload: str):
        self.topic = "ble/beacons/raw"
        self.payload = payload.encode()

if __name__ == "__main__":
    engine = PositioningEngine()
    engine.start()