import asyncio, websockets, json
from mqtt_handler import CONTROL  # <-- импортируем, чтобы менять глобалку

clients = set()

async def handler(ws):
    clients.add(ws)
    try:
        async for msg in ws:
            print("[WS CMD]", msg)
            try:
                data = json.loads(msg)
                if data.get("cmd") == "set_freq":
                    val = float(data["value"])
                    if 0.1 <= val <= 10:
                        CONTROL["freq"] = val
                        print(f"[CONTROL] Частота обновлена: {val} Гц")
                elif data.get("cmd") == "start_record":
                    CONTROL["recording"] = True
                    CONTROL["path"] = []
                    print("[CONTROL] Начата запись маршрута")
                elif data.get("cmd") == "stop_record":
                    CONTROL["recording"] = False
                    print(f"[CONTROL] Окончена запись, {len(CONTROL['path'])} точек")
            except Exception as e:
                print("[WS ERROR parsing]", e)
    finally:
        clients.remove(ws)

async def broadcast(msg: str):
    for ws in list(clients):
        try:
            await ws.send(msg)
        except:
            clients.remove(ws)

async def start_ws():
    server = await websockets.serve(handler, "0.0.0.0", 8080)
    print("[WS] listening on ws://0.0.0.0:8080/ws")
    return server
