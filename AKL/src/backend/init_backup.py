from fastapi import FastAPI
from contextlib import asynccontextmanager
from threading import Thread

import mqtt_server


def on_app_start():
    mqtt_thread = Thread(target=mqtt_server.mqtt_run, daemon=True)
    mqtt_thread.run()


@asynccontextmanager
def lifespan(app: FastAPI):
    on_app_start()
    yield


app = FastAPI(lifespan=lifespan)
