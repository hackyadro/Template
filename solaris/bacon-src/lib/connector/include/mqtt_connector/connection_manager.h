#pragma once

#include <memory>
#include <atomic>
#include <thread>
#include <mutex>

#include "types.h"

// Forward declarations Paho MQTT
namespace mqtt {
    class async_client;
    class callback;
}

// Forward declaration
namespace mqtt_connector {
    class MqttClient;
}

namespace mqtt_connector {

/**
 * @brief Класс для управления подключением к MQTT брокеру
 */
class ConnectionManager {
public:
    ConnectionManager();
    ~ConnectionManager();

    /**
     * @brief Подключение к MQTT брокеру
     * @param config Конфигурация подключения
     * @return true если подключение успешно
     */
    bool connect(const ConnectionConfig& config);

    /**
     * @brief Отключение от MQTT брокера
     */
    void disconnect();

    /**
     * @brief Проверка состояния подключения
     * @return true если подключен
     */
    bool isConnected() const;

    /**
     * @brief Получение текущего состояния подключения
     * @return Состояние подключения
     */
    ConnectionState getConnectionState() const;

    /**
     * @brief Установка callback для изменения состояния подключения
     * @param callback Функция обработки изменений состояния
     */
    void setConnectionCallback(ConnectionCallback callback);

    /**
     * @brief Установка callback для обработки ошибок
     * @param callback Функция обработки ошибок
     */
    void setErrorCallback(ErrorCallback callback);

    /**
     * @brief Получение клиента MQTT (внутреннее)
     * @return Указатель на MQTT клиент
     */
    mqtt::async_client* getClient();

    /**
     * @brief Включение/отключение автоматического переподключения
     * @param enable true для включения автоматического переподключения
     * @param retry_interval Интервал между попытками в секундах
     */
    void setAutoReconnect(bool enable, int retry_interval = 5);

    /**
     * @brief Получение информации о последней ошибке
     * @return Строка с описанием ошибки
     */
    std::string getLastError() const;

    /**
     * @brief Установка нового состояния подключения
     * @param state Новое состояние
     */
    void setState(ConnectionState state);

    /**
     * @brief Обработка ошибки
     * @param error Описание ошибки
     */
    void handleError(const std::string& error);

    void setMqttClient(mqtt_connector::MqttClient* mgr) { mgr_ = mgr; } // HardCode

private:
    std::unique_ptr<mqtt::async_client> client_;
    std::unique_ptr<mqtt::callback> callback_;
    
    ConnectionConfig config_;
    std::atomic<ConnectionState> connection_state_;
    ConnectionCallback connection_callback_;
    ErrorCallback error_callback_;
    
    std::atomic<bool> auto_reconnect_;
    int retry_interval_;
    std::thread reconnect_thread_;
    std::atomic<bool> should_stop_;
    
    mutable std::mutex state_mutex_;
    std::string last_error_;

    mqtt::callback* cb_; // HardCode
    mqtt_connector::MqttClient* mgr_; // HardCode

    /**
     * @brief Поток автоматического переподключения
     */
    void reconnectLoop();
};

} // namespace mqtt_connector
