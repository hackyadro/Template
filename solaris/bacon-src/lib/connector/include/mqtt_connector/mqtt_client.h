#pragma once

#include "types.h"
#include "message_handler.h"
#include "message_objects/BLE.h"
#include "connection_manager.h"
#include "navigator/navigator.h"

#include <mqtt/callback.h>
#include <memory>
#include <vector>
#include <mutex>
#include <thread>
#include <atomic>
#include <condition_variable>

#include <QObject>
#include <QPointF>
#include <QPair>
#include <QList>

namespace mqtt_connector {

/**
 * @brief Основной класс MQTT клиента для приема сообщений
 */
class MqttClient : public QObject {
    Q_OBJECT
    
public:
    MqttClient();
    ~MqttClient();

    /**
     * @brief Инициализация и подключение к MQTT брокеру
     * @param config Конфигурация подключения
     * @return true если подключение успешно
     */
    bool initialize(const ConnectionConfig& config);

    /**
     * @brief Отключение от брокера и очистка ресурсов
     */
    void shutdown();

    /**
     * @brief Подписка на топик
     * @param topic Топик для подписки (поддерживает wildcards: +, #)
     * @param qos Quality of Service уровень (0, 1, 2)
     * @param callback Функция обработки сообщений для этого топика
     * @return true если подписка успешна
     */
    bool subscribe(const std::string& topic, int qos = 0, MessageCallback callback = nullptr);

    /**
     * @brief Отписка от топика
     * @param topic Топик для отписки
     * @return true если отписка успешна
     */
    bool unsubscribe(const std::string& topic);

    /**
     * @brief Публикация сообщения
     * @param message Сообщение для публикации
     * @return true если публикация успешна
     */
    bool publish(const Message& message);

    /**
     * @brief Публикация сообщения (расширенное)
     * @param topic Топик
     * @param payload Содержимое сообщения
     * @param qos Quality of Service уровень
     * @param retained Флаг retained
     * @return true если публикация успешна
     */
    bool publish(const std::string& topic, const std::string& payload, int qos = 0, bool retained = false);

    /**
     * @brief Проверка состояния подключения
     * @return true если подключен к брокеру
     */
    bool isConnected() const;

    /**
     * @brief Получение текущего состояния подключения
     * @return Состояние подключения
     */
    ConnectionState getConnectionState() const;

    /**
     * @brief Регистрация обработчика сообщений по умолчанию
     * @param callback Функция обработки всех сообщений
     */
    void setDefaultMessageHandler(MessageCallback callback);

    /**
     * @brief Установка обработчика изменений состояния подключения
     * @param callback Функция обработки изменений состояния
     */
    void setConnectionStateHandler(ConnectionCallback callback);

    /**
     * @brief Установка обработчика ошибок
     * @param callback Функция обработки ошибок
     */
    void setErrorHandler(ErrorCallback callback);

    /**
     * @brief Получение списка активных подписок
     * @return Вектор топиков, на которые подписан клиент
     */
    std::vector<std::string> getActiveSubscriptions() const;

    /**
     * @brief Включение/отключение автоматического переподключения
     * @param enable true для включения
     * @param retry_interval Интервал между попытками в секундах
     */
    void setAutoReconnect(bool enable, int retry_interval = 5);

    /**
     * @brief Получение статистики клиента
     * @return Строка с информацией о состоянии
     */
    std::string getStatus() const;

    void setBLEBeaconState(const std::string& key, const std::vector<message_objects::BLEBeaconState>& states);
    void addBLEBeaconState(const std::string& key, const message_objects::BLEBeaconState& state);
    
    void clearBLEBeaconStates() {
        std::lock_guard<std::mutex> lock(m_data_mutex_);
        m_data.clear();
    }

    bool BLEBeaconContains(const std::string& name);

    Q_SIGNALS:
    void addPathPoint(const QPointF &pos);
    void setConnectStatus(const QString &status);

public slots:
    void initOnChange(const QString &url);
    void setFreqOnChange(float freq);
    void setBeacons(const QList<QPair<QString, QPointF>> &newBeacons);

private:
    std::unique_ptr<ConnectionManager> connection_manager_;
    std::unique_ptr<MessageHandler> message_handler_;
    
    std::vector<std::string> subscriptions_;
    mutable std::mutex subscriptions_mutex_;
    
    ConnectionConfig current_config_;
    bool initialized_;

    /**
     * @brief Внутренний обработчик входящих сообщений
     * @param message Полученное сообщение
     */
    void onMessageReceived(const Message& message);

    /**
     * @brief Восстановление подписок после переподключения
     */
    void restoreSubscriptions();

    float m_freq = 1.0f;
    mutable std::mutex m_freq_mutex_;

    std::map<std::string, std::vector<message_objects::BLEBeaconState>> m_data;
    mutable std::mutex m_data_mutex_;

    std::vector<message_objects::BLEBeacon> m_beacons;
    mutable std::mutex m_beacons_mutex_;

    std::unique_ptr<navigator::Navigator> navigator_;

    std::thread processing_thread_;
    std::atomic<bool> should_stop_processing_{false};
    std::condition_variable processing_cv_;
    std::mutex processing_mutex_;

    /**
     * @brief Основная функция потока обработки данных
     */
    void dataProcessingLoop();
};

} // namespace mqtt_connector
