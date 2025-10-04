# cmake_minimum_required(VERSION 3.16)

project(connector VERSION 1.0.0)

# set(CMAKE_CXX_STANDARD 17)
# set(CMAKE_CXX_STANDARD_REQUIRED ON)

# option(BUILD_STATIC "Build static library" ON)

find_package(Threads REQUIRED)
find_package(Eigen3 REQUIRED)

# set(CMAKE_PREFIX_PATH "${CMAKE_PREFIX_PATH};~/Qt/6.8.3/gcc_64")

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(Qt6 COMPONENTS Widgets QUIET)

set(CMAKE_AUTOMOC ON)

set(CONNECTOR_SOURCES
    src/mqtt_connector/mqtt_client.cpp
    src/mqtt_connector/message_handler.cpp
    src/mqtt_connector/connection_manager.cpp
    src/navigator/navigator.cpp
    src/config/config.cpp
)

set(CONNECTOR_HEADERS
    include/mqtt_connector/mqtt_client.h
    include/mqtt_connector/message_handler.h
    include/mqtt_connector/connection_manager.h
    include/mqtt_connector/types.h
    include/message_objects/BLE.h
    include/navigator/navigator.h
    include/config/config.h
    include/json.hpp
)

qt_add_library(
    connector
    ${CONNECTOR_SOURCES}
    ${CONNECTOR_HEADERS}
)

list(APPEND CMAKE_PREFIX_PATH "/usr/local")
set(CMAKE_LIBRARY_PATH "${CMAKE_LIBRARY_PATH}:/usr/local/lib")
set(CMAKE_INCLUDE_PATH "${CMAKE_INCLUDE_PATH}:/usr/local/include")

find_package(PkgConfig QUIET)
if(PKG_CONFIG_FOUND)
    pkg_check_modules(PAHO_MQTT_CPP paho-mqttpp3)
endif()

if(NOT PAHO_MQTT_CPP_FOUND)
    message(STATUS "Поиск Paho MQTT библиотек вручную...")
    
    find_path(PAHO_MQTT_INCLUDE_DIR 
        NAMES mqtt/async_client.h
        PATHS /usr/local/include /usr/include
        NO_DEFAULT_PATH
    )
    
    find_library(PAHO_MQTTPP3_LIB
        NAMES paho-mqttpp3 libpaho-mqttpp3
        PATHS /usr/local/lib /usr/lib
        NO_DEFAULT_PATH
    )
    
    find_library(PAHO_MQTT3AS_LIB
        NAMES paho-mqtt3as libpaho-mqtt3as
        PATHS /usr/local/lib /usr/lib /usr/lib/x86_64-linux-gnu
        NO_DEFAULT_PATH
    )
    
    find_library(PAHO_MQTT3C_LIB
        NAMES paho-mqtt3c libpaho-mqtt3c
        PATHS /usr/local/lib /usr/lib /usr/lib/x86_64-linux-gnu
        NO_DEFAULT_PATH
    )
    
    if(PAHO_MQTT_INCLUDE_DIR AND PAHO_MQTTPP3_LIB)
        message(STATUS "Найдены Paho MQTT библиотеки:")
        message(STATUS "  Заголовочные файлы: ${PAHO_MQTT_INCLUDE_DIR}")
        message(STATUS "  C++ библиотека: ${PAHO_MQTTPP3_LIB}")

        if(PAHO_MQTT3AS_LIB)
            message(STATUS "  C библиотека (async): ${PAHO_MQTT3AS_LIB}")
        endif()
        if(PAHO_MQTT3C_LIB)
            message(STATUS "  C библиотека (sync): ${PAHO_MQTT3C_LIB}")
        endif()
        
        set(PAHO_MQTT_FOUND TRUE)
        set(PAHO_MQTT_INCLUDE_DIRS ${PAHO_MQTT_INCLUDE_DIR})
        set(PAHO_MQTT_LIBRARIES ${PAHO_MQTTPP3_LIB})
        
        if(PAHO_MQTT3AS_LIB)
            list(APPEND PAHO_MQTT_LIBRARIES ${PAHO_MQTT3AS_LIB})
        elseif(PAHO_MQTT3C_LIB)
            list(APPEND PAHO_MQTT_LIBRARIES ${PAHO_MQTT3C_LIB})
        endif()
    else()
        message(FATAL_ERROR "Не удалось найти Paho MQTT библиотеки. "
                           "Проверьте установку в /usr/local или /usr")
    endif()
else()
    message(STATUS "Paho MQTT найден через pkg-config")
    set(PAHO_MQTT_FOUND TRUE)
    set(PAHO_MQTT_INCLUDE_DIRS ${PAHO_MQTT_CPP_INCLUDE_DIRS})
    set(PAHO_MQTT_LIBRARIES ${PAHO_MQTT_CPP_LIBRARIES})
endif()

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${PAHO_MQTT_INCLUDE_DIRS}
)

target_link_libraries(connector
    PRIVATE
    ${PAHO_MQTT_LIBRARIES}
    Threads::Threads
    Qt6::Core
    Eigen3::Eigen
)

if(PAHO_MQTT_CPP_FOUND AND PAHO_MQTT_CPP_CFLAGS_OTHER)
    target_compile_options(connector PRIVATE ${PAHO_MQTT_CPP_CFLAGS_OTHER})
endif()

target_include_directories(connector 
    PUBLIC 
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

install(TARGETS connector
    EXPORT connectorTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

install(DIRECTORY include/ DESTINATION include)

install(EXPORT connectorTargets
    FILE connectorTargets.cmake
    NAMESPACE connector::
    DESTINATION lib/cmake/connector
)
