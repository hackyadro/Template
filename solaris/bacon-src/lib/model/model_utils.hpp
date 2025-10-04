#ifndef APP_MODEL_UTILS_HPP
#define APP_MODEL_UTILS_HPP
#include <QPoint>
#include <string>
#include <QList>

namespace model_utils {
    QList<QPointF> parseContent(const std::string &content);
    QString fetchContent(const QList<QPointF> &points);

};


#endif //APP_MODEL_UTILS_HPP