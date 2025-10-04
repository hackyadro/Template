import asyncio
import websockets
import json
from dataclasses import dataclass, asdict

from rssi_locator import RSSILocator, BeaconData
from datetime import datetime
import os
import config
import math


@dataclass
class StatusValue:
    name: str
    value: str


@dataclass
class DeviceData:
    name: str
    rssi: int
    tx_power: int
    last_update: int


class MapServer:
    def __init__(
        self, ws_host="0.0.0.0", ws_port=3030, udp_host="0.0.0.0", udp_port=9999
    ):
        self.connected_clients = set()
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.udp_host = udp_host
        self.udp_port = udp_port

        self.messageLine = "Нет маячков"
        self.deviceData = {}
        self.locator = RSSILocator([])
        self.route_data = []
        self.is_recording_route = False

        beacon_file_path = os.path.join(os.path.dirname(__file__), "beacons.txt")
        if os.path.exists(beacon_file_path):
            try:
                with open(beacon_file_path, "r") as f:
                    content = f.read()
                    self.try_parse_beacon_data(content)
            except Exception as e:
                print(f"Error loading beacons from file: {e}")
                self.messageLine = "Ошибка загрузки маячков из файла"

    async def websocket_handler(self, websocket):
        self.connected_clients.add(websocket)
        print(f"WebSocket client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_websocket_message(data, websocket)
                except json.JSONDecodeError:
                    print(f"Invalid JSON received from {websocket.remote_address}")
                except Exception as e:
                    print(
                        f"Error handling message from {websocket.remote_address}: {e}"
                    )
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)
            print(f"WebSocket client disconnected")

    async def handle_websocket_message(self, data, websocket):
        message_type = data.get("type", "")

        if message_type == "calibrate":
            self.locator.calibrate(data["x"], data["y"])
        elif message_type == "file_upload":
            await self.handle_file_upload(data, websocket)
        elif message_type == "start_route":
            if not self.is_recording_route:
                self.is_recording_route = True
                self.route_data.clear()
                print("Route recording started")
        elif message_type == "finish_route":
            await self.finish_route()
        else:
            print(f"Unknown message type: {message_type}")

    async def handle_file_upload(self, data, websocket):
        content = data.get("content", "")
        if content:
            self.try_parse_beacon_data(content)
            await self.broadcast_state()

    def try_parse_beacon_data(self, content):
        try:
            lines = content.strip().split("\n")
            if len(lines) < 2:
                return

            header = lines[0].strip()
            if header != "Name;X;Y":
                return

            beacons = []
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(";")
                if len(parts) != 3:
                    continue

                try:
                    name = parts[0].strip()
                    x = float(parts[1])
                    y = float(parts[2])
                    beacons.append(BeaconData(name=name, x=x, y=y))
                except ValueError:
                    continue

            if beacons:
                self.locator.update_beacons(beacons)
                self.messageLine = f"Загружено {len(beacons)} маячков"
                print(f"Loaded {len(beacons)} beacons")
                with open(
                    os.path.join(os.path.dirname(__file__), "beacons.txt"), "w"
                ) as f:
                    f.write(content)

        except Exception as e:
            self.messageLine = f"Не смог прочитать файл"
            print(f"Error parsing beacon data: {e}")

    async def finish_route(self):
        if self.is_recording_route:
            self.is_recording_route = False
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.txt"
            content = "X;Y\n"
            for point in self.route_data:
                content += f"{point[0]:.1f};{point[1]:.1f}\n"
            os.makedirs("routes", exist_ok=True)
            filepath = os.path.join("routes", filename)
            try:
                with open(filepath, "w") as f:
                    f.write(content)
                print(f"Route saved to {filepath}")
                self.messageLine = f"Маршрут сохранен"
            except Exception as e:
                print(f"Error saving route: {e}")
                self.messageLine = f"Ошибка сохранения маршрута"
            await self.broadcast_file(filename, content)
            await self.broadcast_state()

    async def broadcast_file(self, filename: str, content: str):
        if self.connected_clients:
            message = json.dumps(
                {
                    "type": "file",
                    "filename": filename,
                    "content": content,
                }
            )
            clients_copy = self.connected_clients.copy()
            for client in clients_copy:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    self.connected_clients.discard(client)

    async def broadcast_state(self):
        if self.connected_clients:
            message = json.dumps(
                {
                    "type": "state",
                    "playerPosition": {"x": self.locator.x, "y": self.locator.y},
                    "objects": [asdict(d) for d in self.locator.get_map_data()],
                    "statusValues": [
                        {"name": k, "value": f"{v.rssi}; {v.tx_power}"}
                        for k, v in self.deviceData.items()
                    ],
                    "messageLine": self.messageLine,
                }
            )
            clients_copy = self.connected_clients.copy()
            for client in clients_copy:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    self.connected_clients.discard(client)
    
    async def broadcast_task(self):
        while True:
            await self.broadcast_state()
            await asyncio.sleep(config.BROADCAST_FREQUENCY)

    def update(self, udp_data):
        current_time = int(datetime.now().timestamp())
        self.deviceData[udp_data["name"]] = DeviceData(
            name=udp_data["name"],
            rssi=udp_data["rssi"],
            tx_power=udp_data["tx_power"],
            last_update=current_time,
        )
        # Remove devices not seen for more than 3 seconds
        expired = []
        for name, device in list(self.deviceData.items()):
            if current_time - device.last_update > 3:
                expired.append(name)
        for name in expired:
            del self.deviceData[name]
        self.locator.on_data(udp_data["name"], udp_data["rssi"], udp_data["tx_power"])

        if self.is_recording_route:
            last_point = self.route_data[-1] if self.route_data else None
            if last_point is None:
                self.route_data.append((self.locator.x, self.locator.y))
            else:
                distance = math.hypot(
                    self.locator.x - last_point[0], self.locator.y - last_point[1]
                )
                if distance >= config.MIN_DISTANCE_TO_UPDATE_ROUTE:
                    self.route_data.append((self.locator.x, self.locator.y))

    class UDPServerProtocol(asyncio.DatagramProtocol):
        def __init__(self, server):
            self.server = server

        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data, addr):
            try:
                message = data.decode("utf-8", errors="replace")
                try:
                    parsed_data = json.loads(message)
                    self.server.update(parsed_data)
                except json.JSONDecodeError:
                    return
            except Exception as e:
                print(f"Error processing UDP message: {e}")

        def error_received(self, exc):
            print(f"UDP server error: {exc}")

    async def udp_server(self):
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: MapServer.UDPServerProtocol(self),
            local_addr=(self.udp_host, self.udp_port),
        )
        print(f"UDP server listening on {self.udp_host}:{self.udp_port}")
        return transport

    async def start(self):
        print(f"Starting WebSocket server on ws://{self.ws_host}:{self.ws_port}")
        await websockets.serve(self.websocket_handler, self.ws_host, self.ws_port)
        asyncio.create_task(self.udp_server())
        asyncio.create_task(self.broadcast_task())
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    server = MapServer()
    asyncio.run(server.start())
