import json
import paho.mqtt.client as mqtt
from typing import Any
from datetime import datetime, timedelta
import math

import rssi_position
from app_state import GlobalState, AppStates
from data import db

large = timedelta(days=1)


class LastPoints():
    def __init__(self):
        self.last_saved = None

    def get_last_saved_delta(self):
        if self.last_saved == None:
            return large
        return datetime.now() - self.last_saved

    def get_last_point():
        db_pos = db.get_last_pos()
        pos = rssi_position.Position(db_pos.x, db_pos.y)
        return pos


BROKER = "localhost"
PORT = 1883
TOPIC = "test/beacons"

global_state = GlobalState()
last_points = LastPoints()


def on_connect(client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
    print("Подключено к брокеру с кодом:", rc)
    client.subscribe(TOPIC)


def json_data_to_station_rssi(data) -> list[rssi_position.StationRssi]:
    res = []
    for i in data:
        try:
            station_rssi = rssi_position.StationRssi(i["name"], i["rssi"])
            res.append(station_rssi)
        except:
            pass
    return res


def print_station(station: rssi_position.StationRssi):
    print(f"{station.name} = {station.rssi}")


def is_valid_pos(pos: rssi_position.Position):
    m_in_sec = 43
    last = last_points.get_last_point()
    if not last:
        return True
    last_time = last_points.get_last_saved_delta()
    dist = math.sqrt((pos.x - last.x) ** 2 + (pos.y - last.y) ** 2)

    time_delta = (datetime.now() - last_time).total_seconds()
    max_dist = m_in_sec * time_delta

    return dist <= max_dist


def on_board_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    global_state.save_last_updated()
    # if global_state.get_state() == AppStates.WAITING:
    #     return
    try:
        payload_str: str = msg.payload.decode()
        data = json.loads(payload_str)
        stations = json_data_to_station_rssi(data)
    except Exception as e:
        print("Ошибка обработки:", e)
        return

    # stations.sort(key=lambda i: i.rssi > - 70)
    # if len(stations) < 3:
    #     return
    pos = rssi_position.get_board_pos(stations)
    # if not is_valid_pos(pos):
    #     return
    db_pos = db.BoardPosition(x=pos.x, y=pos.y)
    db.session.add(db_pos)
    db.session.commit()


def mqtt_run() -> None:
    client: mqtt.Client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_board_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()
