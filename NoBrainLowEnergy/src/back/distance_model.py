import ujson as json

from models import ReceivedMQTTMessage


class Distance_model:
    def __init__(self):
        print("Distance model constructor do smth")

    def Calc(self, message: ReceivedMQTTMessage) -> dict[str, list[float] | list[str]]:
        print("CALC: " + str(message.payload.items()))
