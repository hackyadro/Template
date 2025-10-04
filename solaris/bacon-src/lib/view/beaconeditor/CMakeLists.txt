qt_add_library(beaconeditor STATIC
        beaconeditor.cpp
        beaconeditor.hpp
        beaconeditor.ui
)

target_link_libraries(beaconeditor PUBLIC
        Qt6::Core
        Qt6::Widgets
        model
)

target_include_directories(beaconeditor PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})