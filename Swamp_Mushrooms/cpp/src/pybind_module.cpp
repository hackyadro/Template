#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "pos_estimator.hpp"

namespace py = pybind11;

PYBIND11_MODULE(pos_estimator, m) {
    py::class_<Beacon>(m, "Beacon")
        .def(py::init<>())
        .def_readwrite("x", &Beacon::x)
        .def_readwrite("y", &Beacon::y);

    py::class_<EstimateResult>(m, "EstimateResult")
        .def_readonly("x", &EstimateResult::x)
        .def_readonly("y", &EstimateResult::y)
        .def_readonly("cov_xx", &EstimateResult::cov_xx)
        .def_readonly("cov_xy", &EstimateResult::cov_xy)
        .def_readonly("cov_yy", &EstimateResult::cov_yy);

    py::class_<StatefulEKF>(m, "StatefulEKF")
        .def(py::init(&create_ekf))
        .def("predict", &StatefulEKF::predict)
        .def("update", &StatefulEKF::update)
        .def("get_state", [](StatefulEKF &self){
            double x,y,vx,vy;
            self.get_state(x,y,vx,vy);
            return py::make_tuple(x,y,vx,vy);
        });

    m.def("estimate_position", &estimate_position,
          py::arg("beacons"),
          py::arg("dists"),
          py::arg("variances"),
          py::arg("init_x") = 0.0,
          py::arg("init_y") = 0.0,
          py::arg("use_ekf") = true,
          py::arg("ekf_dt") = 0.1);

    m.def("create_ekf", &create_ekf, py::return_value_policy::take_ownership);
}
