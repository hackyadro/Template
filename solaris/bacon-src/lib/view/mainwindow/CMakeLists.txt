qt_add_library(mainwindow SHARED
        mainwindow.cpp
        mainwindow.hpp
        mainwindow.ui
        ../../../resources.qrc
)

target_link_libraries(mainwindow PUBLIC
        Qt6::Core
        Qt6::Widgets
        beaconeditor
        pathcontroller
        scene
        model
)

target_include_directories(mainwindow PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_BINARY_DIR}
)