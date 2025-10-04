#include "mqtt_connector/message_handler.h"

#include <algorithm>
#include <sstream>

namespace mqtt_connector {

MessageHandler::MessageHandler() = default;

MessageHandler::~MessageHandler() = default;

void MessageHandler::registerHandler(const std::string& topic, MessageCallback callback) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_[topic] = std::move(callback);
}

void MessageHandler::unregisterHandler(const std::string& topic) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_.erase(topic);
}

void MessageHandler::handleMessage(const Message& message) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    
    bool handled = false;
    
    auto it = handlers_.find(message.topic);
    if (it != handlers_.end()) {
        it->second(message);
        handled = true;
    } 
    
    if (!handled && default_handler_) {
        default_handler_(message);
    }
}

void MessageHandler::setDefaultHandler(MessageCallback callback) {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    default_handler_ = std::move(callback);
}

std::vector<std::string> MessageHandler::getRegisteredTopics() const {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    std::vector<std::string> topics;
    topics.reserve(handlers_.size());
    
    for (const auto& [topic, _] : handlers_) {
        topics.push_back(topic);
    }
    
    return topics;
}

void MessageHandler::clearHandlers() {
    std::lock_guard<std::mutex> lock(handlers_mutex_);
    handlers_.clear();
    default_handler_ = nullptr;
}

} // namespace mqtt_connector
