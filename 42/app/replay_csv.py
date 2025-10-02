# replay_csv.py
# python replay_csv.py --source telemetry_storage.csv --dest telemetry_log.csv --rate 5 --loop

import argparse, time, os, sys
from pathlib import Path
from datetime import datetime

def parse_args():
    ap = argparse.ArgumentParser(description="Replay telemetry CSV into another CSV at a given rate.")
    ap.add_argument("--source", "-s", required=True, help="Input CSV to replay (e.g., telemetry_storage.csv)")
    ap.add_argument("--dest", "-d", required=True, help="Output CSV that your app reads (e.g., telemetry_log.csv)")
    ap.add_argument("--rate", "-r", type=float, default=5.0, help="Lines per second (default: 5)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite dest at start (keep only header)")
    ap.add_argument("--loop", action="store_true", help="When source ends, start over (infinite loop)")
    ap.add_argument("--rewrite-ts", action="store_true",
                    help="Rewrite first column (ts) with current time for each line")
    return ap.parse_args()

def main():
    args = parse_args()
    src = Path(args.source)
    dst = Path(args.dest)
    if not src.exists():
        print(f"Source not found: {src}", file=sys.stderr); sys.exit(1)

    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        print("Source is empty.", file=sys.stderr); sys.exit(1)

    header, body = lines[0], lines[1:]

    # prepare dest
    dst.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite or not dst.exists() or dst.stat().st_size == 0:
        dst.write_text(header + "\n", encoding="utf-8")
        print(f"[INIT] wrote header to {dst}")

    delay = 1.0 / max(args.rate, 0.001)

    print(f"[START] Replaying {src} -> {dst} at {args.rate} lines/sec "
          f"{'(loop)' if args.loop else ''} {'(rewrite ts)' if args.rewrite_ts else ''}")

    while True:
        for raw in body:
            line = raw
            if args.rewrite_ts:
                # Перепишем первую колонку (ts) на текущий момент
                parts = line.split(",", 1)
                now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                line = (now + ("," + parts[1] if len(parts) > 1 else ""))

            with dst.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

            time.sleep(delay)

        if not args.loop:
            print("[DONE] reached end of source.")
            break

if __name__ == "__main__":
    main()
