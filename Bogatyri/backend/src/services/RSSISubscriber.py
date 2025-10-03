import json
import threading
import paho.mqtt.client as mqtt

from src.domain.sensor import Sensor


class MqttSensorSubscriber:
    def __init__(self, broker="mqtt", port=1883, topic="sensors/data"):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.sensors: dict[str, Sensor] = {}

        # запуск в отдельном потоке
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        """Внутренний метод для подключения и запуска цикла MQTT"""
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected with result code {rc}")
        client.subscribe(self.topic)

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            sensor = Sensor(**data)
            sensor.name = sensor.name.strip('"\'')
            self.sensors[sensor.name] = sensor
            print(f"[DATA] Received {sensor}")
        except Exception as e:
            print(f"[MQTT] Error parsing message: {e}")

    def get_sensors(self):
        """Вернуть список сенсоров"""
        return [s for s in self.sensors.values()]


    def publish(self, topic: str, message: dict):
        """Отправка сообщения в топик"""
        if isinstance(message, str):
            payload = message
        else:
            payload = json.dumps(message, ensure_ascii=False)

        self.client.publish(topic, payload)
