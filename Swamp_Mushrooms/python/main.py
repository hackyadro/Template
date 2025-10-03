import argparse
import threading
import asyncio
import paho.mqtt.client as mqtt

from mqtt_handler import on_connect, on_message
from estimator import estimator_loop
from ws_server import start_ws, broadcast


def run_estimator(client, device_id, output_topic, freq):
    print("[ESTIMATOR] Loop starting…", flush=True)
    try:
        estimator_loop(client, device_id, output_topic, freq, broadcast)
    except Exception as e:
        print(f"[ESTIMATOR ERROR] {e}", flush=True)


async def main_async(args):
    print("[MAIN] Starting backend...", flush=True)

    # MQTT
    print(f"[MQTT] Connecting to {args.broker}:{args.port}", flush=True)
    client = mqtt.Client(
        userdata={"input_topic": args.input_topic, "device_id": args.device_id}
    )
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
        print("[MQTT] Connected (loop started)", flush=True)
    except Exception as e:
        print(f"[MQTT ERROR] {e}", flush=True)
        return

    # Estimator в отдельном потоке
    threading.Thread(
        target=run_estimator,
        args=(client, args.device_id, args.output_topic, args.freq),
        daemon=True,
    ).start()
    print("[ESTIMATOR] Thread launched", flush=True)

    # WebSocket
    try:
        await start_ws()
        print("[WS] Running at ws://0.0.0.0:8080/ws", flush=True)
    except Exception as e:
        print(f"[WS ERROR] {e}", flush=True)
        return

    print("[MAIN] Backend is fully up and running", flush=True)

    # держим процесс живым
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        print("[MAIN] Event loop cancelled, shutting down", flush=True)


def main():
    print("[INIT] main() entrypoint", flush=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="mqtt")   # сервис mqtt в docker-compose
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--freq", type=float, default=2.0)
    parser.add_argument("--input-topic", default="esp32/ble")
    parser.add_argument("--output-topic", default="ble/position")
    parser.add_argument("--device-id", default="tracker_1")
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("[MAIN] Stopped by user", flush=True)
    except Exception as e:
        print(f"[MAIN ERROR] {e}", flush=True)


if __name__ == "__main__":
    main()
