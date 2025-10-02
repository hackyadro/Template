import paho.mqtt.client as mqtt
import json
import time
from utils.trilateration import Trilateration

class PositioningEngine:
    def __init__(self):
        self.client = mqtt.Client(client_id="PositioningEngine")
        self.trilateration = Trilateration()
        self.current_position = {"x": 0.0, "y": 0.0}
        # EWMA сглаживание для стабильной траектории
        self._smoothing_alpha = 0.3
    
    def on_connect(self, client, userdata, flags, rc):
        print("Positioning Engine Connected to MQTT Broker")
        client.subscribe("ble/beacons/raw")
    
    def on_message(self, client, userdata, msg):
        if msg.topic == "ble/beacons/raw":
            try:
                payload = json.loads(msg.payload.decode())
                beacons = payload.get("beacons", [])
                position = self.trilateration.calculate_position(beacons)
                
                if position:
                    position['timestamp'] = time.time()
                    # EWMA сглаживание
                    smoothed_x = (
                        self._smoothing_alpha * position['x'] +
                        (1 - self._smoothing_alpha) * self.current_position['x']
                    )
                    smoothed_y = (
                        self._smoothing_alpha * position['y'] +
                        (1 - self._smoothing_alpha) * self.current_position['y']
                    )
                    self.current_position = {"x": round(smoothed_x, 2), "y": round(smoothed_y, 2), "timestamp": position['timestamp']}
                    self.publish_position(position)
                else:
                    print("Could not calculate position - not enough beacons")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

    def publish_position(self, position):
        self.client.publish("navigation/position/current", json.dumps(position))
        print(f"Position: ({position['x']}, {position['y']})")
    
    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect("mqtt-broker", 1883, 60)
        self.client.loop_forever()

if __name__ == "__main__":
    engine = PositioningEngine()
    engine.start()