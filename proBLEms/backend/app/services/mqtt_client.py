import json
import time
from typing import Optional, Dict, Any

import paho.mqtt.client as mqtt

from app.mqtt_config import MQTT_CONFIG
from app.services.session_manager import SessionManager


class MQTTClient:
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False

    def connect(self, host: str = "localhost", port: int = 1883,
                username: Optional[str] = None,
                password: Optional[str] = None, keepalive: int = 60):
        self.client = mqtt.Client()
        if username and password:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        try:
            self.client.connect(host, port, keepalive)
            self.client.loop_start()
            print(f"[MQTT] Connecting to {host}:{port} ...")
        except Exception as e:
            print(f"[MQTT] connection error: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            print("[MQTT] Connected")
            client.subscribe(MQTT_CONFIG["topic_scan"])
        else:
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        print("[MQTT] Disconnected")

    def _on_message(self, client, userdata, msg):

        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            topic = msg.topic

            if topic == "indoor/scan/data":
                self._handle_scan_data(data)
            # elif topic.startswith("indoor/control/"):
            #     self._handle_control(topic, data)

        except json.JSONDecodeError as e:
            print(f"[MQTT] JSON decode error: {e}")
        except Exception as e:
            print(f"[MQTT] message error: {e}")

    def _handle_scan_data(self, data: Dict[str, Any]):
        # обязательные поля
        for f in ("beaconReadings",):
            if f not in data:
                print("[MQTT] invalid scan data (missing fields)")
                return

        data.setdefault("timestamp", time.time())
        result = self.session_manager.process_scan_data(data)
        if result.get("status") != "processed":
            print(f"[MQTT] processing failed: {result.get('message')}")

    # def _handle_control(self, topic: str, data: Dict[str, Any]):
    #     command = topic.split("/")[-1]
    #     if command == "start_session":
    #         cfg = data.get("config", {})
    #         res = self.session_manager.start_session(cfg)
    #         self.publish("indoor/control/start_session/response", res)
    #     elif command == "stop_session":
    #         sid = data.get("sessionId")
    #         if sid:
    #             # stop_session — асинхронный; ответ публиковать не будем,
    #             # чтобы не блокировать
    #             import asyncio
    #             if self.session_manager.loop and not \
    #                     self.session_manager.loop.is_closed():
    #                 fut = asyncio.run_coroutine_threadsafe(
    #                     self.session_manager.stop_session(sid),
    #                     self.session_manager.loop)
    #                 try:
    #                     res = fut.result(timeout=3)
    #                     self.publish(
    #                         "indoor/control/stop_session/response", res)
    #                 except Exception as e:
    #                     self.publish(
    #                         "indoor/control/stop_session/response",
    #                         {"status": "error", "message": str(e)})
    #
    # def publish(self, topic: str, payload: Dict[str, Any]):
    #     if self.is_connected and self.client:
    #         try:
    #             self.client.publish(
    #                 topic, json.dumps(payload, ensure_ascii=False))
    #         except Exception as e:
    #             print(f"[MQTT] publish error: {e}")

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
