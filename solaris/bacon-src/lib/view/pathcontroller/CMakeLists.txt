qt_add_library(pathcontroller SHARED
        pathcontroller.cpp
        pathcontroller.hpp
        pathcontroller.ui
        utils.hpp
        utils.cpp
        ../../../resources.qrc
)

target_link_libraries(pathcontroller PUBLIC
        Qt6::Core
        Qt6::Widgets
        model
)

target_include_directories(pathcontroller PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
