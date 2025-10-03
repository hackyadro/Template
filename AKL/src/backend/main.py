from threading import Thread

from fastapi_app.app import app
import mqtt_server

mqtt_thread = Thread(target=mqtt_server.mqtt_run, daemon=True)
mqtt_thread.start()
