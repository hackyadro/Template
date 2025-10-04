#include "utils.hpp"

#include <iostream>
#include <chrono>
#include <iomanip>

bool isValidIPv4WithPort(const QString& input) {
    static const QRegularExpression re(
        R"(^(?:(localhost)|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})):(6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3})$)",
        QRegularExpression::CaseInsensitiveOption);

    return re.match(input).hasMatch();
}

std::string currentTime() {
    using namespace std::chrono;

    // Получаем текущее время
    auto now = system_clock::now();
    auto ms = duration_cast<milliseconds>(now.time_since_epoch()) % 1000;

    // Конвертируем в локальное время
    std::time_t t = system_clock::to_time_t(now);
    std::tm tm = *std::localtime(&t);

    std::ostringstream oss;
    oss << std::setfill('0')
        << std::setw(2) << tm.tm_min << ":"
        << std::setw(2) << tm.tm_sec << ":"
        << std::setw(2) << ms.count() / 10;

    return oss.str();
}