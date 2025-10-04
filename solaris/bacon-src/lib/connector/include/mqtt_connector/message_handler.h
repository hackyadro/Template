#pragma once

#include <unordered_map>
#include <memory>
#include <mutex>

#include "types.h"

namespace mqtt_connector {

/**
 * @brief Класс для обработки входящих MQTT сообщений
 */
class MessageHandler {
public:
    MessageHandler();
    ~MessageHandler();

    /**
     * @brief Регистрация обработчика для конкретного топика
     * @param topic Топик для подписки
     * @param callback Функция обработки сообщений
     */
    void registerHandler(const std::string& topic, MessageCallback callback);

    /**
     * @brief Удаление обработчика для топика
     * @param topic Топик для удаления
     */
    void unregisterHandler(const std::string& topic);

    /**
     * @brief Обработка входящего сообщения
     * @param message Полученное сообщение
     */
    void handleMessage(const Message& message);

    /**
     * @brief Установка обработчика по умолчанию
     * @param callback Функция обработки сообщений по умолчанию
     */
    void setDefaultHandler(MessageCallback callback);

    /**
     * @brief Получение списка зарегистрированных топиков
     * @return Вектор топиков
     */
    std::vector<std::string> getRegisteredTopics() const;

    /**
     * @brief Очистка всех обработчиков
     */
    void clearHandlers();

private:
    std::unordered_map<std::string, MessageCallback> handlers_;
    MessageCallback default_handler_;
    mutable std::mutex handlers_mutex_;
};

} // namespace mqtt_connector
