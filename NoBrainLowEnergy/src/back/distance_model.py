import math
import ujson as json

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency guard
    np = None  # type: ignore[assignment]

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


    def get_position_from_message(self, message: ReceivedMQTTMessage, beacons: dict[str, tuple[float, float]]) -> tuple[float, float]:
        """Estimate position directly from an incoming MQTT message and known beacon positions."""
        distances = self.Calc(message)
        return self.position_from_distances_trilat(distances, beacons)
        # return self.position_from_distances_numpy(distances, beacons)


    def Calc(self, message: ReceivedMQTTMessage) -> dict[str, list[float] | list[str]]:
        """Calculate distance for all beacons in the incoming payload.
        Expects payload shape like:
        {"timestamp": ..., "beacons": [{"rssi": -80, "name": "beacon_3", ...}, ...], ...}
        Returns a dict with two lists aligned by index: names and distances.
        example for testing: {"timestamp": 1, "beacons": [{"rssi": -80, "name": "beacon_3"}]}
        returns: {"names":["beacon_3"],"distances":[21.544346900318832]}}
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
    
    def position_from_distances(self, distances: dict[str, list[float] | list[str]], beacons: dict[str, tuple[float, float]]) -> tuple[float, float]:
        """Estimate position from beacon distances using least squares multilateration.

        Args:
            distances: dict as returned by Calc with aligned "names" and "distances" lists.
            beacons: Mapping of beacon name to (x, y) coordinates in meters.

        Returns:
            Estimated (x, y) position. Returns (nan, nan) when estimation is impossible.
        """

        names = distances.get("names") if isinstance(distances, dict) else []
        dist_values = distances.get("distances") if isinstance(distances, dict) else []

        valid = [
            (float(beacons[str(name)][0]), float(beacons[str(name)][1]), float(dist))
            for name, dist in zip(names or [], dist_values or [])
        ]
        if len(valid) < 2:
            return (float("nan"), float("nan"))

        x1, y1, d1 = valid[0]

        a_rows: list[tuple[float, float]] = []
        b_vals: list[float] = []
        for xi, yi, di in valid[1:]:
            a0 = 2.0 * (x1 - xi)
            a1 = 2.0 * (y1 - yi)
            b = di ** 2 - d1 ** 2 + x1 ** 2 + y1 ** 2 - xi ** 2 - yi ** 2
            a_rows.append((a0, a1))
            b_vals.append(b)

        if not a_rows:
            return (float("nan"), float("nan"))

        ata00 = ata01 = ata10 = ata11 = 0.0
        atb0 = atb1 = 0.0

        for (a0, a1), b in zip(a_rows, b_vals):
            ata00 += a0 * a0
            ata01 += a0 * a1
            ata10 += a1 * a0
            ata11 += a1 * a1
            atb0 += a0 * b
            atb1 += a1 * b

        det = ata00 * ata11 - ata01 * ata10

        if abs(det) < 1e-9:
            # Apply a tiny ridge regularization to keep the system solvable for low-rank cases.
            ridge = 1e-6
            ata00 += ridge
            ata11 += ridge
            det = ata00 * ata11 - ata01 * ata10

            if abs(det) < 1e-12:
                # Fallback to inverse-distance weighted centroid if still singular.
                weight_sum = 0.0
                x_acc = 0.0
                y_acc = 0.0
                for xi, yi, di in valid:
                    weight = 1.0 / max(di, 1e-6)
                    weight_sum += weight
                    x_acc += weight * xi
                    y_acc += weight * yi

                if weight_sum == 0.0:
                    return (float("nan"), float("nan"))

                return (x_acc / weight_sum, y_acc / weight_sum)

        inv_det = 1.0 / det
        x_est = inv_det * (ata11 * atb0 - ata01 * atb1)
        y_est = inv_det * (-ata10 * atb0 + ata00 * atb1)

        return (x_est, y_est)

    def position_from_distances_trilat(
        self,
        distances: dict[str, list[float] | list[str]],
        beacons: dict[str, tuple[float, float]],
    ) -> tuple[float, float]:
        """Estimate position using simple trilateration with the three nearest beacons.

        Args:
            distances: dict as returned by Calc with aligned "names" and "distances" lists.
            beacons: Mapping of beacon name to (x, y) coordinates in meters.

        Returns:
            Estimated (x, y) position. Returns (nan, nan) when estimation is impossible.
        """

        if not isinstance(distances, dict):
            return (float("nan"), float("nan"))

        names = distances.get("names") or []
        dist_values = distances.get("distances") or []

        candidates: list[tuple[float, float, float]] = []
        for name, dist in zip(names, dist_values):
            if not isinstance(name, str):
                name = str(name)
            try:
                coord = beacons[str(name)]
            except Exception:
                continue

            try:
                dist_f = float(dist)
            except Exception:
                continue

            if not math.isfinite(dist_f):
                continue
            if dist_f <= 0.0:
                continue

            x, y = float(coord[0]), float(coord[1])
            candidates.append((x, y, dist_f))

        if len(candidates) < 3:
            return (float("nan"), float("nan"))

        candidates.sort(key=lambda item: item[2])
        anchors = candidates[:3]

        (x1, y1, d1), (x2, y2, d2), (x3, y3, d3) = anchors

        a00 = 2.0 * (x2 - x1)
        a01 = 2.0 * (y2 - y1)
        b0 = d1**2 - d2**2 + x2**2 - x1**2 + y2**2 - y1**2

        a10 = 2.0 * (x3 - x1)
        a11 = 2.0 * (y3 - y1)
        b1 = d1**2 - d3**2 + x3**2 - x1**2 + y3**2 - y1**2

        det = a00 * a11 - a01 * a10

        if abs(det) < 1e-9:
            # Fallback: inverse-distance weighted centroid of the three anchors.
            weights = [1.0 / max(d, 1e-6) for _, _, d in anchors]
            total = sum(weights)
            if total == 0.0:
                return (float("nan"), float("nan"))
            x_est = sum(w * x for (x, _, _), w in zip(anchors, weights)) / total
            y_est = sum(w * y for (_, y, _), w in zip(anchors, weights)) / total
            return (float(x_est), float(y_est))

        inv_det = 1.0 / det
        x_est = inv_det * (a11 * b0 - a01 * b1)
        y_est = inv_det * (-a10 * b0 + a00 * b1)

        return (float(x_est), float(y_est))

    def position_from_distances_numpy(
        self,
        distances: dict[str, list[float] | list[str]],
        beacons: dict[str, tuple[float, float]],
    ) -> tuple[float, float]:
        """Estimate position using NumPy-based least squares multilateration."""

        if np is None:
            raise RuntimeError("numpy is required for position_from_distances_numpy")

        names = distances.get("names") if isinstance(distances, dict) else []
        dist_values = distances.get("distances") if isinstance(distances, dict) else []

        valid = [
            (float(beacons[str(name)][0]), float(beacons[str(name)][1]), float(dist))
            for name, dist in zip(names or [], dist_values or [])
        ]
        if len(valid) < 2:
            return (float("nan"), float("nan"))

        anchors = np.array([[x, y] for x, y, _ in valid], dtype=float)
        dists = np.array([d for _, _, d in valid], dtype=float)

        reference = anchors[0]
        reference_dist = dists[0]

        if len(valid) == 2:
            # With two anchors, the solution lies at intersection of two circles.
            # Use midpoint weighted by inverse distance as a simple approximation.
            # This mirrors the fallback used in the pure Python solver when the system is singular.
            inv_weights = 1.0 / np.maximum(dists, 1e-6)
            weighted = inv_weights[:, np.newaxis] * anchors
            total_weight = np.sum(inv_weights)
            if total_weight == 0:
                return (float("nan"), float("nan"))
            estimate = np.sum(weighted, axis=0) / total_weight
            return (float(estimate[0]), float(estimate[1]))

        A = 2.0 * (reference - anchors[1:])
        ref_norm = np.dot(reference, reference)
        norms = np.sum(anchors[1:] ** 2, axis=1)
        b = dists[1:] ** 2 - reference_dist**2 + ref_norm - norms

        try:
            solution, residuals, rank, _ = np.linalg.lstsq(A, b, rcond=None)
        except np.linalg.LinAlgError:
            solution = np.array([np.nan, np.nan])
            rank = 0

        if not np.all(np.isfinite(solution)) or rank < 2:
            inv_weights = 1.0 / np.maximum(dists, 1e-6)
            weighted = inv_weights[:, np.newaxis] * anchors
            total_weight = float(np.sum(inv_weights))
            if total_weight == 0.0:
                return (float("nan"), float("nan"))
            centroid = np.sum(weighted, axis=0) / total_weight
            return (float(centroid[0]), float(centroid[1]))

        return (float(solution[0]), float(solution[1]))


