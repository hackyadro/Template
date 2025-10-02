import os
from dotenv import load_dotenv
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "hackyadro/+/anchors/+/measurement")
BACKEND_DB = os.getenv("BACKEND_DB", "data/backend.sqlite")
BEACONS_FILE = os.getenv("BEACONS_FILE", "data/standart.beacons")
PATH_OUT = os.getenv("PATH_OUT", "data/output.path")
TEAM = os.getenv("TEAM", "YOUR_TEAM_NAME")
