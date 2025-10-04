#include "model_utils.hpp"

#include <QList>

namespace model_utils {
    QList<QPointF> parseContent(const std::string &content) {
        QList<QPointF> result;

        // Преобразуем std::string в QString
        QString data = QString::fromStdString(content);

        // Разделяем на строки
        QStringList lines = data.split('\n', Qt::SkipEmptyParts);

        // Пропускаем заголовок (первую строку)
        for (int i = 1; i < lines.size(); ++i) {
            QString line = lines[i].trimmed();
            if (line.isEmpty()) continue;

            // Разделяем на значения X и Y
            QStringList values = line.split(';');
            if (values.size() != 2) {
                continue;
            }

            // Функция для преобразования строки в double с учетом обоих разделителей
            auto parseDouble = [](const QString &str) -> double {
                QString normalized = str;
                // Заменяем запятую на точку для корректного преобразования
                normalized = normalized.replace(',', '.');
                bool ok;
                double value = normalized.toDouble(&ok);
                if (!ok) {
                    return 0.0;
                }
                return value;
            };

            double x = parseDouble(values[0]);
            double y = parseDouble(values[1]);

            result.append(QPointF(x, y));
        }

        return result;
    }

    QString fetchContent(const QList<QPointF> &points) {
        QStringList lines;
        lines.append("X;Y");

        for (const QPointF &point: points) {
            // Форматируем с точностью до 2 знаков после запятой
            QString xStr = QString::number(point.x(), 'f', 2).replace('.', ',');
            QString yStr = QString::number(point.y(), 'f', 2).replace('.', ',');

            lines.append(xStr + ";" + yStr);
        }
        return lines.join("\n");
    }
};
