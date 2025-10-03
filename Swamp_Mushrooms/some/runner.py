import argparse, json, time, threading
from estimator import Estimator
from mqtt_client import make_client

BEACONS = {
    "UCUVUVUVUVUVUVUVVUVUV": (-1.0, -0.7),
    "KKKKKKKKKKKKKKKKKKKKK": (0.7, 4.0),
    "ZZZZZZZZZZZZZZZZZZZZZ": (0.7, -0.7),
}

BEACON_PARAMS = {k: {"tx_power": -70.0, "n": 3.3} for k in BEACONS.keys()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--freq", type=float, default=2.0)
    parser.add_argument("--input-topic", default="esp32/ble")
    parser.add_argument("--output-topic", default="ble/position")
    parser.add_argument("--device-id", default="tracker_1")
    args = parser.parse_args()

    est = Estimator(BEACONS, BEACON_PARAMS, window_s=5.0, freq_hz=args.freq)
    client = make_client(args.broker, args.port, args.input_topic, args.device_id, est, args.output_topic)

    def loop():
        while True:
            res = est.step()
            if res:
                out = {
                    "device_id": args.device_id,
                    "timestamp": int(time.time() * 1e6),
                    **res,
                }
                client.publish(args.output_topic, json.dumps(out))
            time.sleep(1.0 / args.freq)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    client.loop_forever()

if __name__ == "__main__":
    main()
