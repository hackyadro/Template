import ujson as json

from models import ReceivedMQTTMessage


class Distance_model:
    def __init__(self):
        # Environmental constant (path-loss exponent). Typical indoor: 2.0 - 3.0
        self.env_const = 3
        print("Distance model constructor do smth")

    def dist(self, rssi: float, baseline: float) -> float:
        """Estimate distance from RSSI using log-distance path loss model.
        d = 10 ** ((TxPower - RSSI) / (10 * n))
        where TxPower is the baseline (reference RSSI at 1 meter), n is env_const.
        """
        try:
            return float(10 ** ((baseline - float(rssi)) / (10.0 * float(self.env_const))))
        except Exception:
            return float("nan")

    def Calc(self, message: ReceivedMQTTMessage) -> dict[str, list[float] | list[str]]:
        """Calculate distance for all beacons in the incoming payload.
        Expects payload shape like:
        {"timestamp": ..., "beacons": [{"rssi": -80, "name": "beacon_3", ...}, ...], ...}
        Returns a dict with two lists aligned by index: names and distances.
        """
        beacons_baseline_signal = [-40, -40, -40, -40, -40, -40, -40, -40]

        payload = message.payload or {}
        beacons = payload.get("beacons", []) or []

        names: list[str] = []
        distances: list[float] = []

        for b in beacons:
            try:
                name = b.get("name") if isinstance(b, dict) else None
                rssi = b.get("rssi") if isinstance(b, dict) else None

                # Determine baseline: map beacon_N to index N-1 if possible
                baseline = -40.0
                if isinstance(name, str) and name.startswith("beacon_"):
                    try:
                        idx = int(name.split("_")[-1]) - 1
                        if 0 <= idx < len(beacons_baseline_signal):
                            baseline = float(beacons_baseline_signal[idx])
                    except Exception:
                        pass

                if rssi is None:
                    continue

                d = self.dist(float(rssi), baseline)
                names.append(name if name else str(b.get("address", "unknown")))
                distances.append(d)
            except Exception:
                # Skip malformed entries
                continue

        return {"names": names, "distances": distances}

