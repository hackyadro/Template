import subprocess
from pathlib import Path

def write_params_file(path: Path, update_time_seconds):
    millis = str(int(update_time_seconds * 1000))
    with open(str(path.absolute()), 'w') as f:
        f.write(millis)

    subprocess.run(['mpremote', 'cp', str(path), ':params.txt'])

def run_mpremote(update_time_seconds: float = 1.0, line_callback=None):
    current_dir = Path(__file__).parent
    params_file = current_dir / 'params.txt'
    write_params_file(params_file, update_time_seconds)

    device_script = current_dir / 'ble_device_tracker.py'

    if not device_script.exists():
        print(f"Ошибка: файл {device_script} не найден")
        return

    proc = subprocess.Popen(
        ['mpremote', 'run', str(device_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    try:
        for line in proc.stdout:
            if line_callback:
                    line_callback(line)
            else:
                print(line, end='')
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    run_mpremote(1)