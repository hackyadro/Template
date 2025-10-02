import os
MQTT_CONFIG = {
    "broker_host": os.getenv("MQTT_HOST", "localhost"),
    "broker_port": int(os.getenv("MQTT_PORT", "1883")),
    "username": os.getenv("MQTT_USERNAME"),
    "password": os.getenv("MQTT_PASSWORD"),
    "keepalive": 60,
    "topic_scan": "indoor/scan/data",
    "topic_config": "indoor/config",
}
