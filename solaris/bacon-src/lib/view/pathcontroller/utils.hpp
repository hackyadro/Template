#ifndef APP_PATHCONTROLLER_UTILS_HPP
#define APP_PATHCONTROLLER_UTILS_HPP

#include <QRegularExpression>
#include <QString>

/**
 * Регулярное выражение:
    - либо "localhost"
    - либо IPv4: 0-255.0-255.0-255.0-255
    - обязательный порт: ":" + 1-65535
*/
bool isValidIPv4WithPort(const QString &input);

std::string currentTime();

#endif
