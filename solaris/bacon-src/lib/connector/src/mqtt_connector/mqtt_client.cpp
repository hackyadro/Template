#include "mqtt_connector/mqtt_client.h"

#include <mqtt/async_client.h>
#include <mqtt/message.h>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <sstream>

#include <QPointF>

namespace mqtt_connector {

MqttClient::MqttClient()
    : connection_manager_(std::make_unique<ConnectionManager>()),
      message_handler_(std::make_unique<MessageHandler>()),
      initialized_(false) {
    navigator_ = std::make_unique<navigator::Navigator>(m_beacons);
}

MqttClient::~MqttClient() {
    shutdown();
}

bool MqttClient::initialize(const ConnectionConfig& config) {
    if (initialized_) {
        shutdown();
    }

    current_config_ = config;

    connection_manager_->setConnectionCallback([this](ConnectionState state) {
        if (state == ConnectionState::CONNECTED) {
            restoreSubscriptions();
        }
    });

    connection_manager_->setMqttClient(this);

    if (!connection_manager_->connect(config)) {
        emit setConnectStatus("Disconnected");
        return false;
    }

    initialized_ = true;

    // subscribe("hakaton/board", 1, [this, &out](const Message& msg) {
    //     std::cout << "Message received: " << msg.payload << std::endl;
    // });

    // Hardcode:
    connection_manager_->getClient()->subscribe("hakaton/board", 1);

    should_stop_processing_ = false;
    processing_thread_ = std::thread(&MqttClient::dataProcessingLoop, this);

    emit setConnectStatus("Connected");

    return true;
}

void MqttClient::shutdown() {
    emit setConnectStatus("Disconnected");

    if (processing_thread_.joinable()) {
        should_stop_processing_ = true;
        processing_cv_.notify_all();
        processing_thread_.join();
    }

    if (!initialized_) {
        return;
    }

    {
        std::lock_guard<std::mutex> lock(subscriptions_mutex_);
        for (const auto& topic : subscriptions_) {
            try {
                if (connection_manager_->isConnected()) {
                    auto client = connection_manager_->getClient();
                    if (client) {
                        auto token = client->unsubscribe(topic);
                        token->wait_for(std::chrono::seconds(5));
                    }
                }
            } catch (const std::exception&) {
                // Игнорируем ошибки при отключении
            }
        }
        subscriptions_.clear();
    }

    connection_manager_->disconnect();
    message_handler_->clearHandlers();

    initialized_ = false;
}

bool MqttClient::subscribe(const std::string& topic, int qos,
                           MessageCallback callback) {
    if (!initialized_ || !connection_manager_->isConnected()) {
        return false;
    }

    try {
        auto client = connection_manager_->getClient();
        if (!client) {
            return false;
        }

        if (callback) {
            message_handler_->registerHandler(topic, callback);
        }

        auto token = client->subscribe(topic, qos);
        token->wait_for(std::chrono::seconds(10));

        if (token->get_return_code() == mqtt::ReasonCode::SUCCESS) {
            std::lock_guard<std::mutex> lock(subscriptions_mutex_);
            if (std::find(subscriptions_.begin(), subscriptions_.end(),
                          topic) == subscriptions_.end()) {
                subscriptions_.push_back(topic);
            }
            return true;
        }

        return false;

    } catch (const std::exception& e) {
        connection_manager_->setErrorCallback([e](const std::string&) {
            // Обработка ошибки подписки
        });
        return false;
    }
}

bool MqttClient::unsubscribe(const std::string& topic) {
    if (!initialized_ || !connection_manager_->isConnected()) {
        return false;
    }

    try {
        auto client = connection_manager_->getClient();
        if (!client) {
            return false;
        }

        auto token = client->unsubscribe(topic);
        token->wait_for(std::chrono::seconds(10));

        if (token->get_return_code() == mqtt::ReasonCode::SUCCESS) {
            message_handler_->unregisterHandler(topic);

            std::lock_guard<std::mutex> lock(subscriptions_mutex_);
            subscriptions_.erase(std::remove(subscriptions_.begin(),
                                             subscriptions_.end(), topic),
                                 subscriptions_.end());

            return true;
        }

        return false;

    } catch (const std::exception&) {
        return false;
    }
}

bool MqttClient::publish(const Message& message) {
    if (!initialized_ || !connection_manager_->isConnected()) {
        return false;
    }

    try {
        auto client = connection_manager_->getClient();
        if (!client) {
            return false;
        }

        auto mqtt_msg = mqtt::make_message(message.topic, message.payload);
        mqtt_msg->set_qos(message.qos);
        mqtt_msg->set_retained(message.retained);

        auto token = client->publish(mqtt_msg);
        token->wait_for(std::chrono::seconds(10));

        return token->get_return_code() == mqtt::ReasonCode::SUCCESS;

    } catch (const std::exception&) {
        return false;
    }
}

bool MqttClient::publish(const std::string& topic, const std::string& payload,
                         int qos, bool retained) {
    return publish(Message(topic, payload, qos, retained));
}

bool MqttClient::isConnected() const {
    return initialized_ && connection_manager_->isConnected();
}

ConnectionState MqttClient::getConnectionState() const {
    if (!initialized_) {
        return ConnectionState::DISCONNECTED;
    }
    return connection_manager_->getConnectionState();
}

void MqttClient::setDefaultMessageHandler(MessageCallback callback) {
    message_handler_->setDefaultHandler(callback);
}

void MqttClient::setConnectionStateHandler(ConnectionCallback callback) {
    if (connection_manager_) {
        connection_manager_->setConnectionCallback(callback);
    }
}

void MqttClient::setErrorHandler(ErrorCallback callback) {
    if (connection_manager_) {
        connection_manager_->setErrorCallback(callback);
    }
}

std::vector<std::string> MqttClient::getActiveSubscriptions() const {
    std::lock_guard<std::mutex> lock(subscriptions_mutex_);
    return subscriptions_;
}

void MqttClient::setAutoReconnect(bool enable, int retry_interval) {
    if (connection_manager_) {
        connection_manager_->setAutoReconnect(enable, retry_interval);
    }
}

std::string MqttClient::getStatus() const {
    std::ostringstream status;

    status << "MQTT Client Status:\n";
    status << "  Initialized: " << (initialized_ ? "Yes" : "No") << "\n";
    status << "  Connected: " << (isConnected() ? "Yes" : "No") << "\n";
    status << "  State: ";

    switch (getConnectionState()) {
        case ConnectionState::DISCONNECTED:
            status << "Disconnected";
            break;
        case ConnectionState::CONNECTING:
            status << "Connecting";
            break;
        case ConnectionState::CONNECTED:
            status << "Connected";
            break;
        case ConnectionState::RECONNECTING:
            status << "Reconnecting";
            break;
        case ConnectionState::FAILED:
            status << "Failed";
            break;
    }

    status << "\n";
    status << "  Broker: " << current_config_.broker_host << ":"
           << current_config_.broker_port << "\n";
    status << "  Client ID: " << current_config_.client_id << "\n";

    {
        std::lock_guard<std::mutex> lock(subscriptions_mutex_);
        status << "  Active subscriptions: " << subscriptions_.size() << "\n";
        for (const auto& topic : subscriptions_) {
            status << "    - " << topic << "\n";
        }
    }

    if (connection_manager_) {
        auto lastError = connection_manager_->getLastError();
        if (!lastError.empty()) {
            status << "  Last error: " << lastError << "\n";
        }
    }

    return status.str();
}

void MqttClient::setBLEBeaconState(
    const std::string& key,
    const std::vector<message_objects::BLEBeaconState>& states) {
    std::lock_guard<std::mutex> lock(m_data_mutex_);
    m_data[key] = states;
}

void MqttClient::addBLEBeaconState(
    const std::string& key, const message_objects::BLEBeaconState& state) {
    std::lock_guard<std::mutex> lock(m_data_mutex_);
    m_data[key].push_back(state);
}

bool MqttClient::BLEBeaconContains(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_beacons_mutex_);
    return std::any_of(m_beacons.begin(), m_beacons.end(),
                       [&name](const message_objects::BLEBeacon& beacon) {
                           return beacon.name_ == name;
                       });
}

void MqttClient::initOnChange(const QString& url) {
    QStringList parts = url.split(':');
    ConnectionConfig config;

    if (parts.size() == 2) {
        config.broker_host = parts[0].toStdString();
        config.broker_port = parts[1].toInt();
    } else {
        config.broker_host = url.toStdString();
        config.broker_port = 1883;  // стандартный порт MQTT
    }

    config.client_id = "client_id";
    config.keep_alive_interval = 60;
    config.clean_session = true;
    config.connection_timeout = 30;
    config.use_ssl = false;

    initialize(config);
}

void MqttClient::setFreqOnChange(float freq) {
    std::lock_guard<std::mutex> lock(m_freq_mutex_);
    m_freq = freq;
}

void MqttClient::setBeacons(const QList<QPair<QString, QPointF>>& newBeacons) {
    std::lock_guard<std::mutex> lock(m_beacons_mutex_);
    m_beacons.clear();
    for (const auto& pair : newBeacons) {
        std::cout << pair.first.toStdString() << std::endl;
        message_objects::BLEBeacon beacon;
        beacon.name_ = pair.first.toStdString();
        beacon.x_ = pair.second.x();
        beacon.y_ = pair.second.y();
        m_beacons.push_back(beacon);
    }
    navigator_->setKnownBeacons(m_beacons);
}

void MqttClient::onMessageReceived(const Message& message) {
    message_handler_->handleMessage(message);
}

void MqttClient::restoreSubscriptions() {
    std::lock_guard<std::mutex> lock(subscriptions_mutex_);

    for (const auto& topic : subscriptions_) {
        try {
            auto client = connection_manager_->getClient();
            if (client) {
                client->subscribe(topic, 0);
            }
        } catch (const std::exception&) {
            // Игнорируем ошибки восстановления подписок
        }
    }
}

void MqttClient::dataProcessingLoop() {
    while (!should_stop_processing_) {
        std::unique_lock<std::mutex> lock(processing_mutex_);
        float current_freq;
        {
            std::lock_guard<std::mutex> freq_lock(m_freq_mutex_);
            current_freq = m_freq;
        }

        auto wait_duration =
            std::chrono::milliseconds(static_cast<int>(1000.0f / current_freq));

        if (processing_cv_.wait_for(lock, wait_duration) ==
            std::cv_status::no_timeout) {
            if (should_stop_processing_) {
                break;
            }
        }

        std::vector<std::pair<std::string,
                              std::vector<message_objects::BLEBeaconState>>>
            collected_data;
        {
            std::lock_guard<std::mutex> data_lock(m_data_mutex_);
            if (!m_data.empty()) {
                std::cout << m_data.size() << std::endl;
                for (const auto& pair : m_data) {
                    collected_data.emplace_back(pair.first, pair.second);
                }
                m_data.clear();
            }
        }

        // Если есть данные для обработки
        if (!collected_data.empty()) {
            // Преобразуем данные для навигатора
            std::vector<message_objects::BLEBeaconState> all_states;
            for (const auto& pair : collected_data) {
                for (const auto& state : pair.second) {
                    all_states.push_back(state);
                }
            }

            // Вызываем calculatePosition если есть навигатор и данные
            if (navigator_ && !all_states.empty()) {
                try {
                    auto position = navigator_->calculatePosition(all_states);
                    QPointF pos(position.first, position.second);
                    
                    // Испускаем сигнал с результатом
                    emit addPathPoint(pos);
                } catch (const std::exception& e) {
                    std::cerr << "Error calculating position: " << e.what() << std::endl;
                }
            }
        }
    }
}

}  // namespace mqtt_connector
