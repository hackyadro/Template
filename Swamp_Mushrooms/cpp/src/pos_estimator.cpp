#include "pos_estimator.hpp"
#include <ceres/ceres.h>
#include <ceres/covariance.h>
#include <Eigen/Dense>
#include <iostream>
#include <cmath>
using Eigen::Matrix2d;
using Eigen::Vector2d;

// ---------------- Residual ----------------
struct Residual {
    Residual(double bx, double by, double di, double w) : bx(bx), by(by), di(di), weight(w) {}
    template <typename T>
    bool operator()(const T* const xy, T* residual) const {
        T dx = xy[0] - T(bx);
        T dy = xy[1] - T(by);
        T pred = sqrt(dx*dx + dy*dy);
        residual[0] = T(weight) * (pred - T(di));
        return true;
    }
    double bx, by, di, weight;
};

// ---------------- Stateful EKF implementation ----------------
StatefulEKF::StatefulEKF() {
    x_ = y_ = vx_ = vy_ = 0.0;
    initialized_ = false;
    for (int i=0;i<16;++i) P_[i]=0.0;
}

void StatefulEKF::predict(double dt) {
    if (!initialized_) return;
    // state transition for constant velocity
    x_ = x_ + vx_*dt;
    y_ = y_ + vy_*dt;
    // simple process noise
    double q_pos = 0.01;
    double q_vel = 0.1;
    // add process noise to diagonal of P
    P_[0] += q_pos;
    P_[5] += q_pos;
    P_[10] += q_vel;
    P_[15] += q_vel;
}

void StatefulEKF::update(double mx, double my, double cov_xx, double cov_xy, double cov_yy) {
    if (!initialized_) {
        x_ = mx; y_ = my; vx_ = 0.0; vy_ = 0.0;
        // init covariance with measurement covariance
        for (int i=0;i<16;++i) P_[i]=0.0;
        P_[0] = cov_xx;
        P_[1] = cov_xy;
        P_[4] = cov_xy;
        P_[5] = cov_yy;
        initialized_ = true;
        return;
    }
    // measurement matrix H = [1 0 0 0; 0 1 0 0]
    // P (4x4), R (2x2)
    // compute S = H*P*H^T + R --> 2x2
    double S00 = P_[0] + cov_xx;
    double S01 = P_[1] + cov_xy;
    double S10 = P_[4] + cov_xy;
    double S11 = P_[5] + cov_yy;
    // compute K = P*H^T * S^{-1} --> 4x2
    double detS = S00*S11 - S01*S10;
    if (fabs(detS) < 1e-12) return;
    double invS00 = S11/detS;
    double invS01 = -S01/detS;
    double invS10 = -S10/detS;
    double invS11 = S00/detS;
    // P*H^T rows: first col = [P00, P10, P20, P30]^T (but P is row-major)
    double Ph0 = P_[0];
    double Ph1 = P_[4];
    double Ph2 = P_[8];
    double Ph3 = P_[12];
    double Ph0b = P_[1];
    double Ph1b = P_[5];
    double Ph2b = P_[9];
    double Ph3b = P_[13];
    // K = [Ph0 Ph0b; Ph1 Ph1b; Ph2 Ph2b; Ph3 Ph3b] * invS
    double K[8];
    K[0] = Ph0*invS00 + Ph0b*invS10;
    K[1] = Ph0*invS01 + Ph0b*invS11;
    K[2] = Ph1*invS00 + Ph1b*invS10;
    K[3] = Ph1*invS01 + Ph1b*invS11;
    K[4] = Ph2*invS00 + Ph2b*invS10;
    K[5] = Ph2*invS01 + Ph2b*invS11;
    K[6] = Ph3*invS00 + Ph3b*invS10;
    K[7] = Ph3*invS01 + Ph3b*invS11;
    // innovation
    double y0 = mx - x_;
    double y1 = my - y_;
    // state update
    x_ += K[0]*y0 + K[1]*y1;
    y_ += K[2]*y0 + K[3]*y1;
    vx_ += K[4]*y0 + K[5]*y1;
    vy_ += K[6]*y0 + K[7]*y1;
    // update covariance P = (I - K*H)*P
    // compute KH (4x4) where KH = K * H -> only first two columns of K used
    double KH[16] = {0};
    // KH = K * H -> rows: i, cols j
    // since H has ones at (0,0) and (1,1) only, KH will place K columns into first two columns
    KH[0] = K[0]; KH[1] = K[1]; KH[2] = 0; KH[3] = 0;
    KH[4] = K[2]; KH[5] = K[3]; KH[6] = 0; KH[7] = 0;
    KH[8] = K[4]; KH[9] = K[5]; KH[10]=0; KH[11]=0;
    KH[12]= K[6]; KH[13]= K[7]; KH[14]=0; KH[15]=0;
    double IminusKH[16];
    for (int i=0;i<16;++i) {
        IminusKH[i] = ((i%5)==0 ? 1.0 : 0.0) - KH[i];
    }
    // newP = (I-KH)*P
    double newP[16] = {0};
    for (int r=0;r<4;++r) for (int c=0;c<4;++c) {
        double s=0;
        for (int k=0;k<4;++k) s += IminusKH[r*4+k]*P_[k*4+c];
        newP[r*4+c]=s;
    }
    for (int i=0;i<16;++i) P_[i]=newP[i];
}

void StatefulEKF::get_state(double &out_x, double &out_y, double &out_vx, double &out_vy) {
    out_x = x_; out_y = y_; out_vx = vx_; out_vy = vy_;
}

StatefulEKF* create_ekf() {
    return new StatefulEKF();
}

// ---------------- estimate_position ----------------
EstimateResult estimate_position(const std::vector<Beacon>& beacons,
                                  const std::vector<double>& dists,
                                  const std::vector<double>& variances,
                                  double init_x, double init_y,
                                  bool use_ekf, double ekf_dt) {
    const int N = (int)beacons.size();
    if (N < 2) {
        return {init_x, init_y, 1e6, 0.0, 1e6};
    }

    double xy[2] = {init_x, init_y};

    ceres::Problem problem;
    for (int i = 0; i < N; ++i) {
        double var = variances.size() == N ? variances[i] : 1.0;
        double w = (var <= 0.0) ? 1.0 : 1.0 / sqrt(var); // inverse stddev
        ceres::CostFunction* cost = new ceres::AutoDiffCostFunction<Residual,1,2>(
            new Residual(beacons[i].x, beacons[i].y, dists[i], w));
        ceres::LossFunction* loss = new ceres::HuberLoss(0.7);
        problem.AddResidualBlock(cost, loss, xy);
    }

    ceres::Solver::Options options;
    options.minimizer_progress_to_stdout = false;
    options.max_num_iterations = 100;
    options.function_tolerance = 1e-10;
    options.gradient_tolerance = 1e-12;
    options.linear_solver_type = ceres::DENSE_QR;
    options.num_threads = 1;

    ceres::Solver::Summary summary;
    ceres::Solve(options, &problem, &summary);

    double cov_xx = 0.0, cov_xy = 0.0, cov_yy = 0.0;
    if (N >= 2) {
        ceres::Covariance::Options cov_options;
        ceres::Covariance covariance(cov_options);
        std::vector<std::pair<const double*, const double*>> cov_blocks;
        cov_blocks.emplace_back(xy, xy);
        if (covariance.Compute(cov_blocks, &problem)) {
            double cov_mat[4];
            covariance.GetCovarianceBlock(xy, xy, cov_mat);
            cov_xx = cov_mat[0];
            cov_xy = cov_mat[1];
            cov_yy = cov_mat[3];
        }
    }

    EstimateResult res;
    res.x = xy[0];
    res.y = xy[1];
    res.cov_xx = cov_xx;
    res.cov_xy = cov_xy;
    res.cov_yy = cov_yy;
    return res;
}
