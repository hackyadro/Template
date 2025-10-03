# collect_rssi.py
import paho.mqtt.client as mqtt
import json
import csv
import argparse
import time

BROKER = "193.106.150.201"
PORT = 1883
TOPIC = "beacons/discovered"
OUTPUT_CSV = "rssi_measurements.csv"

parser = argparse.ArgumentParser()
parser.add_argument("--distance", type=float, required=True, help="Фактическое расстояние (м) от контроллера до маяков")
args = parser.parse_args()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Подключились к брокеру")
        client.subscribe(TOPIC)
    else:
        print("Ошибка подключения:", rc)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        if "beacons" not in data:
            return
        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for b in data["beacons"]:
                writer.writerow([b["name"], args.distance, b["rssi"]])
        print(f"Сохранили {len(data['beacons'])} измерений при d={args.distance} м")
    except Exception as e:
        print("Ошибка обработки:", e)

def main():
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["beacon_name", "distance_m", "rssi"])

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
