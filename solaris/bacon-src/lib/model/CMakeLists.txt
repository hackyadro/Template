qt_add_library(model STATIC
        abstractitem.hpp
        beacon.hpp
        espobject.hpp
        model.cpp
        model.hpp
        model_utils.cpp
        model_utils.hpp
)

target_link_libraries(model PUBLIC
        Qt6::Core
        Qt6::Widgets
        connector
)

target_include_directories(model PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
