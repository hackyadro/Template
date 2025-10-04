#pragma once

#include <string>
#include <functional>
#include <memory>
#include <vector>

namespace mqtt_connector {

/**
 * @brief Структура для хранения настроек подключения к MQTT брокеру
 */
struct ConnectionConfig {
    std::string broker_host = "localhost";  ///< Хост MQTT брокера
    int broker_port = 1883;                 ///< Порт MQTT брокера
    std::string client_id;                  ///< Идентификатор клиента
    int keep_alive_interval = 60;           ///< Интервал keep-alive в секундах
    bool clean_session = true;              ///< Флаг очистки сессии
    int connection_timeout = 30;            ///< Таймаут подключения в секундах
    bool use_ssl = false;                   ///< Использовать SSL/TLS
};

/**
 * @brief Структура для представления MQTT сообщения
 */
struct Message {
    std::string topic;                      ///< Топик сообщения
    std::string payload;                    ///< Содержимое сообщения
    int qos = 0;                           ///< Quality of Service (0, 1, 2)
    bool retained = false;                  ///< Флаг сохранения сообщения
    
    Message() = default;
    Message(const std::string& topic, const std::string& payload, int qos = 0, bool retained = false)
        : topic(topic), payload(payload), qos(qos), retained(retained) {}
};

/**
 * @brief Перечисление состояний подключения
 */
enum class ConnectionState {
    DISCONNECTED,   ///< Отключен
    CONNECTING,     ///< Подключается
    CONNECTED,      ///< Подключен
    RECONNECTING,   ///< Переподключается
    FAILED          ///< Ошибка подключения
};

using MessageCallback = std::function<void(const Message& message)>;
using ConnectionCallback = std::function<void(ConnectionState state)>;
using ErrorCallback = std::function<void(const std::string& error)>;

} // namespace mqtt_connector
