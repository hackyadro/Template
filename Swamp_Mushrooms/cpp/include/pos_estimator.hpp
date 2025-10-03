#pragma once
#include <vector>

struct Beacon {
    double x = 0;
    double y = 0;
};

struct EstimateResult {
    double x=0;
    double y=0;
    double cov_xx=0;
    double cov_xy=0;
    double cov_yy=0;
};

// Stateful EKF class for smoothing across calls
class StatefulEKF {
public:
    StatefulEKF();
    // predict with dt (seconds)
    void predict(double dt);
    // update with position measurement (x,y) and covariance (2x2)
    void update(double mx, double my, double cov_xx, double cov_xy, double cov_yy);
    // get current state
    void get_state(double &out_x, double &out_y, double &out_vx, double &out_vy);
private:
    // internal state: x, y, vx, vy
    double x_, y_, vx_, vy_;
    // covariance 4x4 stored row-major
    double P_[16];
    bool initialized_;
};

EstimateResult estimate_position(const std::vector<Beacon>& beacons,
                                  const std::vector<double>& dists,
                                  const std::vector<double>& variances,
                                  double init_x, double init_y,
                                  bool use_ekf = true, double ekf_dt = 0.1);

// expose a factory to get a persistent EKF object from Python
StatefulEKF* create_ekf();
