Quick start (after building C++ module):

1. Build the C++ module (see root README). Copy resulting pos_estimator.so to this python/ folder or install to PYTHONPATH.
2. Install python deps: pip install paho-mqtt
3. Run calibration if you have dataset:
   python calibrate_tx_n.py measurements.csv
4. Edit mqtt_runner.py BEACONS and BEACON_PARAMS to your coordinates and calibrated tx_power/n.
5. Run:
   python mqtt_runner.py --broker <broker> --port 1883 --freq 2.0

mqtt_runner will subscribe to 'ble/raw' and publish positions to 'ble/position'.
