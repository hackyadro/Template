cmake_minimum_required(VERSION 3.14)
project(pos_estimator LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Eigen3 REQUIRED)
find_package(Ceres REQUIRED)
find_package(Python3 COMPONENTS Development Interpreter REQUIRED)
find_package(pybind11 REQUIRED)

add_library(pos_estimator MODULE
    src/pos_estimator.cpp
    src/pybind_module.cpp
)

target_include_directories(pos_estimator PRIVATE
    ${EIGEN3_INCLUDE_DIRS}
    ${CERES_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(pos_estimator PRIVATE
    ${CERES_LIBRARIES}
    pybind11::module
    Python3::Python
)

# Чтобы имя .so было красивым (без "lib" впереди)
set_target_properties(pos_estimator PROPERTIES PREFIX "" SUFFIX ".so")
