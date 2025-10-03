POS_TRACKER_FULL
=================

This archive contains a high-accuracy BLE trilateration stack:
- C++ core using Ceres (weighted robust nonlinear least squares) + Eigen
- Stateful EKF implemented in C++ and exposed to Python via pybind11
- Python orchestrator (MQTT subscription, buffering, windowing, calibration helper)

Build notes:
- Requires: Eigen3, Ceres, pybind11 (system dev packages recommended)
- On Ubuntu: install libceres-dev, libeigen3-dev, pybind11-dev, and other build tools.
- Run cmake/make from project root; copy produced pos_estimator*.so into python/ folder.

See python/README.md for quick start.
